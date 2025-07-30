import pandas as pd
import random as rd
import math
import copy

numReps = 10
numProducts = 3

options = pd.read_csv('../options_%sproducts_revised.csv'%numProducts)
forbidden = pd.read_csv('../forbiddenPairs_%sproducts_choice_revised.csv'%numProducts)
optionArray = list(options['Option'])    
numOptions = len(optionArray)
swappable = [1,3]
        
for networkID in ['Gowalla']:
    nodes0 = pd.read_csv('nodes_%s.csv'%(networkID))
    
    for rep in range(numReps):
        
        nodes = copy.deepcopy(nodes0)
        
        prodSum = {}
        for prod in range(1,numProducts+1):
            prodSum[prod] = 0
        
        optionColumn = {}
        for option in optionArray:
            optionColumn[option] = []       
 
        for u in nodes['Node']:
            rpw = {}
            for option in optionArray:
                rpw[option] = 1 + 2 * (float(option) - 0.5 + rd.random())
            for option in swappable:
                if rd.random() < 0.42:
                    rpw_option = rpw[option]
                    rpw[option] = rpw[option+1]
                    rpw[option+1] = rpw_option
            for option in optionArray:                
                optionColumn[option] += [1 / rpw[option]]
                
        for option in optionArray:
            nodes['Option%s'%option] = optionColumn[option]
                
        nodes.to_csv(r'nodes_3products_choice_revised/nodes_%s_%s.csv'%(networkID,rep), index = False)#Check
        
        
        
        
        
        
        
        

