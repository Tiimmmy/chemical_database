#导入需要的模块
import random, rdkit, os, sys
from rdkit import Chem
import pdb

#设置导入和导出路径
strInFilePath = "data/core"
strOutPath = "data/in_core/"

#设置母核标记
listRandomSymbol = ["[A1]", "[A2]", "[A3]", "[A4]", "[A5]", "[A6]", "[A7]", "[A8]", "[A9]"]


for i in os.listdir(strInFilePath):
    filepath =  strInFilePath+'/'+i
    idx = 0
    mols = Chem.SDMolSupplier(filepath)
    print(filepath)
    for mol in mols:        
        counter_star = 0
        smi = Chem.MolToSmiles(mol)
        for f in smi:
            if f=='*':
                counter_star+=1
        for j in range(counter_star):
            frag = frag.replace('*', random.choice(listRandomSymbol),1) 
        dirs=strOutPath+i.split('.')[0]+'/'
        if not os.path.exists(dirs):
            os.makedirs(dirs)
        filename=dirs+"{:0>5d}.smi".format(idx)
        fileOut = open(filename, 'w')
        fileOut.write(frag + '\n')
        idx += 1
  
os.listdir(strInFilePath)
fileOut.close()
