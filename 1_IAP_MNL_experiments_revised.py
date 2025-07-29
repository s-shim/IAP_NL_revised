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

for (networkID,repNum) in [(9,50),(5,50),(3,50),(4,50),(2,50),(0,10),(8,10),(6,10),(7,10),(1,10)]:

    machineColumn = []    
    netColumn = []
    nodColumn = []
    edgColumn = []
    proColumn = []
    disColumn = []
    repColumn = []
    metColumn = []
    revColumn = []
    infColumn = []
    
    optColumn = []
    logColumn = []
    boundColumn = []
    ncColumn = []
    timeColumn = []
    
    for rep in range(repNum):        
        lines = pd.read_csv('lines/lines_%s.csv'%networkID)
        nodes = pd.read_csv('nodes_%sproducts_choice_revised/%s/nodes_%s_%s.csv'%(numProducts,networkID,networkID,rep))
        #lines = pd.read_csv('yt_lines.csv')
        #nodes = pd.read_csv('yt_nodes_20220123.csv')
        options = pd.read_csv('options_%sproducts_revised.csv'%numProducts)
        forbidden = pd.read_csv('forbiddenPairs_%sproducts_choice_revised.csv'%numProducts)
        
        
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
        model.setParam('LogFile', 'result_MNL_revised/grblog/grblog_MNL_%s_%s_%s.txt'%(networkID,rep,machineName))        
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
        varNameArray = []
        varValueArray = []
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
        optSolution.to_csv(r'result_MNL_revised/opt/opt_MNL_%s_%s_%s.csv'%(networkID,rep,machineName), index = False)#Check
        
        machineColumn += [machineName]    
        netColumn += [networkID]
        nodColumn += [len(G.nodes())]
        edgColumn += [len(G.edges())]
        proColumn += [numProducts]
        disColumn += [len(options['Option'])]
        repColumn += [rep]
        metColumn += ['MNL']
        revColumn += [totalRevenue]
        infColumn += [len(confG.subgraph(offered).edges())]
        optColumn += [model.objVal]
        boundColumn += [bounding]
        ncColumn += [model.NodeCount]

        timeColumn += [model.Runtime]
                
        listZip = list(zip(machineColumn,netColumn,nodColumn,edgColumn,proColumn,disColumn,repColumn,metColumn,boundColumn,optColumn,revColumn,infColumn,ncColumn,timeColumn))
        colName = ['Machine','networkID','nodes','edges','products','options','rep','method','Bounding','ILP OPT','accurate OPT','infeasibility','B&B','Runtime']
        result = pd.DataFrame(listZip,columns = colName)
        result.to_csv(r'result_MNL_revised/result_MNL_%s_%s.csv'%(networkID,machineName), index = False)#Check
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
