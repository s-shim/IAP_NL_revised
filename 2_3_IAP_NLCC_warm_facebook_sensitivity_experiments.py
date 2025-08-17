# conflict graph model with general number of options solved by GUROBI

from gurobipy import *
import pandas as pd
import networkx as nx  
import copy  
from itertools import combinations
import math
import socket
import glob

machineName = socket.gethostname()

logSum = 0.5
numProducts = 3

bounding = True
warm = True
timeLimit = True

for (networkID,repNum,TL) in [(9,50,3600),(5,50,3600),(3,50,3600),(4,50,3600),(2,50,3600)]:#[(0,10,3600*5),(8,10,3600*5),(6,10,3600*5),(7,10,3600*5),(1,10,3600*5)]:
    for bounding in [True,False]:
    
        machineColumn = []    
        netColumn = []
        nodColumn = []
        edgColumn = []
        proColumn = []
        disColumn = []
        repColumn = []
        metColumn = []
        warmColumn = []
        revColumn = []
        infColumn = []
        
        optColumn = []
        bdColumn = [] 
        logColumn = []
        boundColumn = []
        ncColumn = []
        timeColumn = []
        tlColumn = []
        
        initialColumn = []
        
        lines = pd.read_csv('lines/lines_%s.csv'%networkID)
        options = pd.read_csv('options_%sproducts_revised.csv'%numProducts)
        forbidden = pd.read_csv('forbiddenPairs_%sproducts_choice_revised.csv'%numProducts)
        
        for rep in range(repNum):        
        
            nodes = pd.read_csv('nodes_%sproducts_choice_revised/%s/nodes_%s_%s.csv'%(numProducts,networkID,networkID,rep))    
            if warm == True:
                incumbent = pd.read_csv('2_result_Sensitivity/3_result_LS/lopt/lopt_DLS_Net%s_Rep%s_logSum%s.csv'%(networkID,rep,int(logSum * 100))) 
                [initialObj] = incumbent.loc[incumbent['varName']=='revenue','varVal']
                
            G = nx.Graph()
            for u in nodes['Node']:
                G.add_node(u)
                
            for line in lines['Line']:
                [source_line] = lines.loc[lines['Line']==line,'Source']
                [target_line] = lines.loc[lines['Line']==line,'Target']
                G.add_edge(source_line,target_line)
            
            product = {}
            pw = {}
            confG = nx.Graph()
            for u in G.nodes():
                for p in options['Option']:
                    confG.add_node((u,p))
                    [product_p] = options.loc[options['Option']==p,'Product']
                    [price_p] = options.loc[options['Option']==p,'Price']
                    [preference_u_p] = nodes.loc[nodes['Node']==u,'Option%s'%p]
                    product[p] = product_p
                    pw[u,p] = preference_u_p
                    confG.nodes[(u,p)]['Price'] = price_p
                    confG.nodes[(u,p)]['Preference'] = preference_u_p        
                    
            for u in G.nodes():
                for pair in forbidden['Pair']:
                    [source_pair] = forbidden.loc[forbidden['Pair']==pair,'Source']
                    [target_pair] = forbidden.loc[forbidden['Pair']==pair,'Target']
                    confG.add_edge((u,source_pair),(u,target_pair))
            
            for (u,v) in G.edges():
                for pair in forbidden['Pair']:
                    [source_pair] = forbidden.loc[forbidden['Pair']==pair,'Source']
                    [target_pair] = forbidden.loc[forbidden['Pair']==pair,'Target']
                    confG.add_edge((u,source_pair),(v,target_pair))
                    confG.add_edge((u,target_pair),(v,source_pair))
            
            nodeList = list(G.nodes())
            confNodeList = list(confG.nodes())
            optionList = list(options['Option'])
                
            # ILP Model
            model = Model('Inequity Aversion Pricing')
            
            ## Employ Variables
            x_vars = []
            x_names = []
            for (u,p) in confG.nodes():
                x_vars += [(u,p)]
                x_names += ['X[%s,%s]'%(u,p)]
            X = model.addVars(x_vars, vtype = GRB.BINARY, name = x_names)
                
            p_vars = []
            p_names = []
            for u in G.nodes():
                p_vars += [(u,0)]
                p_names += ['P[%s,%s]'%(u,0)]
            
            for (u,q) in confG.nodes():
                p_vars += [(u,q)]
                p_names += ['P[%s,%s]'%(u,q)]
            P = model.addVars(p_vars, vtype = GRB.CONTINUOUS, name = p_names)
            
            if warm == True:
                tpwInc = {}
                for u in G.nodes():
                    tpwInc[u] = 0
        
                optionsTo = {}
                for u in G.nodes():
                    optionsTo[u] = []
                    
                xValInc = {}
                for (u,p) in confG.nodes():
                    [xVal_u_p] = incumbent.loc[incumbent['varName']=='X[%s,%s]'%(u,p),'varVal']
                    X[u,p].Start = xVal_u_p
                    if xVal_u_p > 1 - 0.0001:
                        xValInc[u,p] = 1
                        tpwInc[u] += pow(pw[u,p],1/logSum)
                        optionsTo[u] += [p]
                    if xVal_u_p <  0.0001:
                        xValInc[u,p] = 0
                
                for (u,q) in confG.nodes():
                    if xValInc[u,q] == 0:
                        P[u,q].Start = 0
                    else:
                        P[u,q].Start = pow(tpwInc[u],logSum) / (1 + pow(tpwInc[u],logSum)) * pow(pw[u,q],1/logSum) / tpwInc[u]
                
                
            ## Add Constraints
            for ((u,p),(v,q)) in confG.edges():
                LHS = [(1,X[u,p]),(1,X[v,q])]
                model.addConstr(LinExpr(LHS)<=1, name='Eq.BE(%s,%s,%s,%s)'%(u,p,v,q))
            
            #if bounding == False:    
            for (u,q) in confG.nodes():
                LHS = [(1,P[u,q]),(-1,X[u,q])]
                model.addConstr(LinExpr(LHS)<=0, name='Eq.Bound(%s,%s)'%(u,q))
                
            for u in G.nodes():
                LHS = [(1,P[u,0])]
                for q in options['Option']:
                    LHS += [(1,P[u,q])]
                model.addConstr(LinExpr(LHS)==1, name='Eq.sumProb(%s)'%(u))
                        
            for u in G.nodes():
                for q in options['Option']:
                    for r in options['Option']:
                        if q != r:
                            LHS = [(1,P[u,q]),(-math.pow(pw[u,q]/pw[u,r],1/logSum),P[u,r])]
                            LHS += [(1,X[u,r])]
                            model.addConstr(LinExpr(LHS)<=1, name='Eq.oddsRatio(%s,%s,%s)'%(u,q,r))
            
            
            ## Set Objective
            objTerms = []
            for (u,q) in confG.nodes():
                [price_q] = options.loc[options['Option']==q,'Price']
                objTerms += [(price_q,P[u,q])]
            
            model.setObjective(LinExpr(objTerms), GRB.MAXIMIZE)
            
            
            def mycallback(model, where):
                if where == GRB.Callback.MIPSOL:
                    # make a list of edges selected in the solution
                    xVal = {}
                    pVal = {}
             
                    for (u,q) in confNodeList:
                        xVal[u,q] = model.cbGetSolution(X[u,q])
            
                    for u in nodeList:
                        pVal[u,0] = model.cbGetSolution(P[u,0])
                    
                    for (u,q) in confNodeList:
                        pVal[u,q] = model.cbGetSolution(P[u,q])
                        
                    for u in nodeList:
                        stable_u = []
                        nonStable_u = []
                        for q in optionList:
                            if xVal[u,q] > 1 - 0.0001:
                                stable_u += [q]
                            if xVal[u,q] < 0 + 0.0001:
                                nonStable_u += [q]
                                
                        if len(optionList) > len(stable_u) + len(nonStable_u):
                            print('### Error: len(optionList) > len(stable_u) + len(nonStable_u)')
            
                        if len(stable_u) > 0:
                            z_X_u = 0
                            for q in stable_u:
                                z_X_u += math.pow(pw[u,q],1/logSum)
                            
                            wHat = math.pow(z_X_u,logSum) / (1 + math.pow(z_X_u,logSum))
                        
                            p_u = 0
                            for q in optionList:
                                p_u += pVal[u,q]
                                
                            if p_u > wHat + 0.0001:
                                dwHat = logSum * math.pow(z_X_u,logSum - 1) / math.pow(1 + math.pow(z_X_u,logSum),2)
                                LHS = []
                                for q in optionList:
                                    LHS += [(1,P[u,q])]
                                    LHS += [(- dwHat * math.pow(pw[u,q],1/logSum),X[u,q])]
                                
                                rhs = wHat
                                for q in stable_u:
                                    rhs = rhs - dwHat * math.pow(pw[u,q],1/logSum)
            
                                model.cbLazy(LinExpr(LHS) <= rhs)
            
                            if p_u < wHat - 0.0001:
                                LHS = []
                                for q in optionList:
                                    LHS += [(+1,P[u,q])]
                                for q in stable_u:
                                    LHS += [(-1,X[u,q])]
                                for q in nonStable_u:
                                    LHS += [(+1,X[u,q])]
                    
                                rhs = wHat - len(stable_u)
            
                                model.cbLazy(LinExpr(LHS) >= rhs)
                                
                                
            if bounding == True:    
                # bounding variables (Start)
                productList = []
                for q in optionList:
                    productList += [product[q]]
                productList = list(set(productList))
                
                ub = {}
                lb = {}
                for u in nodeList:
                    for q in optionList:
                        ub[u,q] = math.pow(pw[u,q],1/logSum)
                        lb[u,q] = math.pow(pw[u,q],1/logSum)
                
                best = {}
                for u in nodeList:
                    for prod in productList:
                        best[u,prod] = 0
                        for q in optionList:
                            if product[q] == prod and best[u,prod] < math.pow(pw[u,q],1/logSum):
                                best[u,prod] = math.pow(pw[u,q],1/logSum)
                
                for u in nodeList:
                    for q in optionList:
                        for prod in productList:
                            if product[q] != prod:
                                ub[u,q] += best[u,prod]
                                
                for (u,q) in confNodeList:
                    coeff_LB = math.pow(ub[u,q],logSum) / (1 + math.pow(ub[u,q],logSum)) * math.pow(pw[u,q],1/logSum) / ub[u,q]
                    coeff_UB = pw[u,q] / (1 + pw[u,q])
                    LHS_LB = [(1,P[u,q]),(-coeff_LB,X[u,q])]    
                    LHS_UB = [(1,P[u,q]),(-coeff_UB,X[u,q])]    
                    model.addConstr(LinExpr(LHS_LB)>=0 - 0.0001, name='Eq.LowerBound(%s,%s)'%(u,q))
                    model.addConstr(LinExpr(LHS_UB)<=0 + 0.0001, name='Eq.UpperBound(%s,%s)'%(u,q))
                
                            
            
            # update and solve the model
            model.update()
            model.Params.lazyConstraints = 1
            #model.setParam('Cuts',3)    
            model.setParam('LogFile','2_result_Sensitivity/grblog/grblog_NLCC_%s_%s_logSum%s_Bound%s_warm%s.txt'%(networkID,rep,int(logSum*100),bounding,warm))        
        
            if timeLimit == True:
                model.setParam('TimeLimit',TL)   
                
            if bounding == True:
                model.setParam('MIPFocus',3)   
                model.setParam('Cuts',0)    
                model.setParam('GomoryPasses',200) # inst1    
                model.setParam('LiftProjectCuts',2) # inst1    
                model.setParam('ImpliedCuts',2)    
                model.setParam('MIRCuts',2)    
                model.setParam('FlowCoverCuts',2)    
                model.setParam('RLTCuts',2)  
                model.setParam('RelaxLiftCuts',2)  
                model.setParam('BQPCuts',2)
            
            model.optimize(mycallback)
            
            
            
            # read the optimal solution
            choice = {}
            tpw = {}
            for u in nodeList:
                choice[u] = []
                tpw[u] = 0
            
            offered = []    
            varNameArray = []
            varValueArray = []
            for v in model.getVars():
                varNameArray += [v.varname]
                varValueArray += [v.x]
                if v.varname[0] == 'X' and v.x > 1 - 0.0001:
                    varName = v.varname.split(',')
                    u = int(varName[0][2:])
                    q = int(varName[-1][:-1])
                    choice[u] += [q]
                    tpw[u] += math.pow(pw[u,q],1/logSum)
                    offered += [(u,q)]    
        
            optSolution = pd.DataFrame(list(zip(varNameArray, varValueArray)),columns =['varName', 'varVal'])
            optSolution.to_csv(r'2_result_Sensitivity/opt/opt_NLCC_%s_%s_logSum%s_Bound%s_warm%s.csv'%(networkID,rep,int(logSum*100),bounding,warm), index = False)#Check
            
            totalRevenue = 0
            for u in nodeList:
                if len(choice[u]) > 0:
                    for q in choice[u]:
                        prob_u_q = math.pow(tpw[u],logSum) / (1 + math.pow(tpw[u],logSum)) * math.pow(pw[u,q],1/logSum) / tpw[u]
                        totalRevenue += confG.nodes[(u,q)]['Price'] * prob_u_q
            
            print('networkID =',networkID)
            print('rep =',rep) 
            print('logSum =',logSum)
            print('bounding =',bounding)
            print('totalRevenue =',totalRevenue)
            print('infeasibility =',len(confG.subgraph(offered).edges()))
        
            machineColumn += [machineName]    
            netColumn += [networkID]
            nodColumn += [len(G.nodes())]
            edgColumn += [len(G.edges())]
            proColumn += [numProducts]
            disColumn += [len(options['Option'])]
            repColumn += [rep]
            metColumn += ['NL']
            warmColumn += [warm]
            revColumn += [totalRevenue]
            initialColumn += [initialObj]
            infColumn += [len(confG.subgraph(offered).edges())]
            optColumn += [model.objVal]
            bdColumn += [model.objBound]
            logColumn += [logSum]
            boundColumn += [bounding]
            ncColumn += [model.NodeCount]
        
            timeColumn += [model.Runtime]
            if timeLimit == True:
        
                tlColumn += [TL]
                    
                listZip = list(zip(machineColumn,netColumn,nodColumn,edgColumn,proColumn,disColumn,repColumn,metColumn,warmColumn,logColumn,boundColumn,initialColumn,bdColumn,optColumn,revColumn,infColumn,ncColumn,timeColumn,tlColumn))
                colName = ['Machine','networkID','nodes','edges','products','options','rep','method','warm','logSum','Bounding','Initial','bestBd','ILP OPT','accurate OPT','infeasibility','B&B','Runtime','Time Limit']
                summary = pd.DataFrame(listZip,columns = colName)
                summary.to_csv(r'2_result_Sensitivity/summary_NLCC_%s_logSum%s_Bound%s_warm%s.csv'%(networkID,int(logSum*100),bounding,warm), index = False)#Check
        
            else:    
        
                listZip = list(zip(machineColumn,netColumn,nodColumn,edgColumn,proColumn,disColumn,repColumn,metColumn,warmColumn,logColumn,boundColumn,initialColumn,bdColumn,optColumn,revColumn,infColumn,ncColumn,timeColumn))
                colName = ['Machine','networkID','nodes','edges','products','options','rep','method','warm','logSum','Bounding','Initial','bestBd','ILP OPT','accurate OPT','infeasibility','B&B','Runtime']
                summary = pd.DataFrame(listZip,columns = colName)
                summary.to_csv(r'2_result_Sensitivity/summary_NLCC_%s_logSum%s_Bound%s_warm%s.csv'%(networkID,int(logSum*100),bounding,warm), index = False)#Check
            
