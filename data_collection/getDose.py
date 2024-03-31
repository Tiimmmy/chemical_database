#get dose info of CTD
import xlrd
import pandas as pd
import re

def getDose(data):
    t1 = 'DOSE/DURATION           : '
    t2 = 'TOXIC'
    pat = re.compile(t1+'(.*?)'+t2, re.S)
    for dose in pat.findall(data):
        Dose=dose
        return Dose


def getSpecies(data):
    t1 = 'SPECIES OBSERVED        : '
    t2 = 'TEST SYSTEM             : '
    t3 = 'DOSE/DURATION'
    pat = re.compile(t1+'(.*?)'+t3, re.S)
    pat2 = re.compile(t2+'(.*?)'+t3, re.S)
    if pat.findall(data) is not None:
        for species in pat.findall(data):
            Species=species
            return Species
    else:
        for species in pat2.findall(data):
            Species=species
            return Species


def getType(data):
    t1 = 'TYPE OF TEST            : '
    t2 = 'ROUTE OF EXPOSURE'
    pat = re.compile(t1+'(.*?)'+t2, re.S)
    for Type in pat.findall(data):        
        return Type


def getToxicity(data):
    t1 = 'TOXIC EFFECTS :'
    t2 = 'REFERENCE'
    pat = re.compile(t1+'(.*?)'+t2, re.S)
    for Toxicity in pat.findall(data):        
        return Toxicity


if __name__ == '__main__':
    in_path = r"D:\OldDrug\ZebraWholeT.xlsx"
    out_path = r"D:\OldDrug\ZebraMutation.csv"
    data = xlrd.open_workbook(in_path)
    table = data.sheets()[1]
    nor = table.nrows
    nol = table.ncols
    for i in range(1,nor):
        cas = table.cell_value(i,0)
        toxicity = table.cell_value(i,1)
        try:
            Dose = getDose(toxicity)
            Species = getSpecies(toxicity)
            Type = getType(toxicity)
            Toxicity = getToxicity(toxicity)
        except Exception as e:
            print(e)
            pass
        #Ddict={'cas-number':cas, 'Dose':Dose, 'Species':Species, 'Type':Type}
        Ddict={'cas-number':cas, 'Dose':Dose, 'Species':Species, 'Type':Type, 'Toxicity':Toxicity}
        print(Ddict)
        df = pd.DataFrame(Ddict,index=[0])
        df.to_csv(out_path,line_terminator="\n",index=False,mode='a',header=None,encoding='utf8')
