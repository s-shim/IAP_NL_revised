# conflict graph model with general number of options solved by GUROBI

from gurobipy import *
import pandas as pd
import networkx as nx  
import copy  
from itertools import combinations
import socket

machineName = socket.gethostname()

numProducts = 3
bounding = False
timeLimit = True
warm = True
logSum = 1

options = pd.read_csv('options_%sproducts_revised.csv'%numProducts)
forbidden = pd.read_csv('forbiddenPairs_%sproducts_choice_revised.csv'%numProducts)

for (networkID,repNum,TL) in [(9,50,3600),(5,50,3600),(3,50,3600),(4,50,3600),(2,50,3600),(0,10,3600*5),(8,10,3600*5),(6,10,3600*5),(7,10,3600*5),(1,10,3600*5)]:

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
    for rep in range(repNum):        
        nodes = pd.read_csv('nodes_%sproducts_choice_revised/%s/nodes_%s_%s.csv'%(numProducts,networkID,networkID,rep))
        #lines = pd.read_csv('yt_lines.csv')
        #nodes = pd.read_csv('yt_nodes_20220123.csv')

        if warm == True:
            logSum = 1
            incumbent = pd.read_csv('2_result_Sensitivity/3_result_LS/lopt/lopt_DLS_Net%s_Rep%s_logSum%s.csv'%(networkID,rep,int(logSum * 100))) 
            [initialObj] = incumbent.loc[incumbent['varName']=='revenue','varVal']
        
        
        G = nx.Graph()
        nodeList = []
        for u in nodes['Node']:
            int_u = int(u)
            G.add_node(int_u)
            nodeList += [int_u]
        
        lineList = []
        for line in lines['Line']:
            [source_line] = lines.loc[lines['Line']==line,'Source']
            [target_line] = lines.loc[lines['Line']==line,'Target']
            u = int(source_line)
            v = int(target_line)
            G.add_edge(u,v)
            lineList += [(u,v)]
        
        optionList = []
        product = {}
        price = {}
        for q in options['Option']:
            optionList += [q]
            [product_q] = options.loc[options['Option']==q,'Product']
            [price_q] = options.loc[options['Option']==q,'Price']
            product[q] = int(product_q)
            price[q] = float(price_q)
        
        forbiddenList = []
        for pair in forbidden['Pair']:
            [source_pair] = forbidden.loc[forbidden['Pair']==pair,'Source']
            [target_pair] = forbidden.loc[forbidden['Pair']==pair,'Target']
            u = int(source_pair)
            v = int(target_pair)
            forbiddenList += [(u,v)]   
        
        pw = {}
        confNodeList = []
        confG = nx.Graph()
        for u in nodeList:
            for q in optionList:
                confG.add_node((u,q))
                confNodeList += [(u,q)]
                [preference_u_q] = nodes.loc[nodes['Node']==u,'Option%s'%q]
                pw[u,q] = float(preference_u_q)
                        
        for u in G.nodes():
            for (source_pair,target_pair) in forbiddenList:
                confG.add_edge((u,source_pair),(u,target_pair))
        
        for (u,v) in lineList:
            for (source_pair,target_pair) in forbiddenList:
                confG.add_edge((u,source_pair),(v,target_pair))
                confG.add_edge((u,target_pair),(v,source_pair))
        

        print()
        print('### MNL Starts')
        print('### networkID =',networkID)
        print('### rep =',rep)
        print('### number of nodes =',len(nodeList))        
        print('### number of edges =',len(G.edges()))        
            
        # ILP Model
        model = Model('Inequity Aversion Pricing')
        
        ## Employ Variables
        x_vars = []
        x_names = []
        for (u,q) in confNodeList:
            x_vars += [(u,q)]
            x_names += ['X[%s,%s]'%(u,q)]
        X = model.addVars(x_vars, vtype = GRB.BINARY, name = x_names)
        
        
        p_vars = []
        p_names = []
        for u in nodeList:
            p_vars += [(u,0)]
            p_names += ['P[%s,%s]'%(u,0)]
        
        for (u,q) in confNodeList:
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
            model.addConstr(LinExpr(LHS)<=1, name='Eq.Conflict(%s,%s,%s,%s)'%(u,p,v,q))
        
        if bounding == False:
            for (u,q) in confNodeList:
                LHS = [(1,P[u,q]),(-1,X[u,q])]
                model.addConstr(LinExpr(LHS)<=0, name='Eq.Bound(%s,%s)'%(u,q))
        
        for u in nodeList:
            LHS = [(1,P[u,0])]
            for q in optionList:
                LHS += [(1,P[u,q])]
            model.addConstr(LinExpr(LHS)==1, name='Eq.sumProb(%s)'%(u))
        
        for u in nodeList:
            for q in optionList:
                LHS = [(1,P[u,q]),(-pw[u,q],P[u,0])]
                model.addConstr(LinExpr(LHS)<=0, name='Eq.UB(%s,%s)'%(u,q))
        
        for u in nodeList:
            for q in optionList:
                LHS = [(1,P[u,0]),(-1 / pw[u,q],P[u,q]),(1,X[u,q])]
                model.addConstr(LinExpr(LHS)<=1, name='Eq.LB(%s,%s)'%(u,q))
        
        ## Set Objective
        objTerms = []
        for (u,q) in confNodeList:
            objTerms += [(price[q],P[u,q])]
        
        model.setObjective(LinExpr(objTerms), GRB.MAXIMIZE)
        
        
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
                    ub[u,q] = pw[u,q]
                    lb[u,q] = pw[u,q]
            
            best = {}
            for u in nodeList:
                for prod in productList:
                    best[u,prod] = 0
                    for q in optionList:
                        if product[q] == prod and best[u,prod] < pw[u,q]:
                            best[u,prod] = pw[u,q]
            
            for u in nodeList:
                for q in optionList:
                    for prod in productList:
                        if product[q] != prod:
                            ub[u,q] += best[u,prod]
                            
            for (u,q) in confNodeList:
                coeff_LB = pw[u,q] / (1 + ub[u,q])
                coeff_UB = pw[u,q] / (1 + lb[u,q])
                LHS_LB = [(1,P[u,q]),(-coeff_LB+0.0001,X[u,q])]    
                LHS_UB = [(1,P[u,q]),(-coeff_UB-0.0001,X[u,q])]    
                model.addConstr(LinExpr(LHS_LB)>=0, name='Eq.LowerBound(%s,%s)'%(u,q))
                model.addConstr(LinExpr(LHS_UB)<=0, name='Eq.UpperBound(%s,%s)'%(u,q))
        
        
        # update and solve the model
        model.update()
        model.setParam('LogFile', '1_result_MNL_revised/grblog/grblog_MNL_%s_%s_%s.txt'%(networkID,rep,machineName))        

        if timeLimit == True:
            model.setParam('TimeLimit',TL)   

        model.optimize()
        
        
        # read the optimal solution
        choice = {}
        tpw = {}
        for u in nodeList:
            choice[u] = []
            tpw[u] = 0
        
        haveOffered = {}
        for j in optionList:
            haveOffered[j] = 0
            
        offered = []    
        varNameArray = ['model.objVal']
        varValueArray = [model.objVal]
        varNameArray += ['model.objBound']
        varValueArray += [model.objBound]
        varNameArray += ['model.Runtime']
        varValueArray += [model.Runtime]
        for v in model.getVars():
            varNameArray += [v.varname]
            varValueArray += [v.x]
            if v.varname[0] == 'X' and v.x > 1 - 0.0001:
                varName = v.varname.split(',')
                u = int(varName[0][2:])
                q = int(varName[-1][:-1])
                # print(v.varname,u,q)
                choice[u] += [q]
                tpw[u] += pw[u,q]
                offered += [(u,q)]
                
                haveOffered[q] += 1
                
        for j in optionList:
            print('haveOffered[%s] ='%j,haveOffered[j])
        
        totalRevenue = 0
        for u in nodeList:
            if len(choice[u]) > 0:
                for q in choice[u]:
                    prob_u_q = pw[u,q] / (1 + tpw[u])
                    totalRevenue += price[q] * prob_u_q
        
        print('totalRevenue =',totalRevenue)
        print('infeasibility =',len(confG.subgraph(offered).edges()))

        optSolution = pd.DataFrame(list(zip(varNameArray, varValueArray)),columns =['varName', 'varVal'])
        optSolution.to_csv(r'1_result_MNL_revised/opt/opt_MNL_%s_%s_%s.csv'%(networkID,rep,machineName), index = False)#Check
        


        machineColumn += [machineName]    
        netColumn += [networkID]
        nodColumn += [len(G.nodes())]
        edgColumn += [len(G.edges())]
        proColumn += [numProducts]
        disColumn += [len(options['Option'])]
        repColumn += [rep]
        metColumn += ['MNL']
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
            summary.to_csv(r'1_result_MNL_revised/result_MNL_%s_logSum%s_Bound%s_warm%s.csv'%(networkID,int(logSum*100),bounding,warm), index = False)#Check
    
        else:    
    
            listZip = list(zip(machineColumn,netColumn,nodColumn,edgColumn,proColumn,disColumn,repColumn,metColumn,warmColumn,logColumn,boundColumn,initialColumn,bdColumn,optColumn,revColumn,infColumn,ncColumn,timeColumn))
            colName = ['Machine','networkID','nodes','edges','products','options','rep','method','warm','logSum','Bounding','Initial','bestBd','ILP OPT','accurate OPT','infeasibility','B&B','Runtime']
            summary = pd.DataFrame(listZip,columns = colName)
            summary.to_csv(r'1_result_MNL_revised/result_MNL_%s_logSum%s_Bound%s_warm%s.csv'%(networkID,int(logSum*100),bounding,warm), index = False)#Check

        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
