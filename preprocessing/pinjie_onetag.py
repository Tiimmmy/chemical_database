#导入需要的库
#import re
#from sys import argv

corepath = r'D:\CADD\Drug-likeness\smile\core_star.smi'
in_core = open(corepath, 'r')
fragpath = r'D:\CADD\Drug-likeness\smile\frag_renum.smi'
in_frag = open(fragpath, 'r') #打开片段文件
outpath = r'D:\CADD\Drug-likeness\smile\compound_update.smi'
out = open(outpath, 'w')

reverse = 0

#得到片段
def GetFrag(in_frag):
    
    frags = in_frag.read() #读取in_frag文件，得到片段smiles式
    frags = frags.replace('\n','') #除去换行符
    frag_list = frags.split('R') #将每个片段放入数组中，备用
    #除去空片段
    for frag in frag_list: 
        if frag == '':
            frag_list.remove('')
    return frag_list

#得到母核数组
def GetCore(in_core):
    cores = in_core.read()
    core_list = cores.split('\n') #将每个母核放入数组中
    return core_list


#仅针对只有一个母核的情况，得到标记数
#def GetCoreNum(in_core):
    
#    core = in_core.read()
#    core_list = core.split('A')
#    core_num = len(core_list)-1
#    if core_list[0] == '':
#        reverse = 1

#    return core_num


#拼接
def BuildMolecule(in_core, in_frags, out):
    frag_list = GetFrag(in_frag)
    core_list = GetCore(in_core)
#    core_num = GetCoreNum(in_core)
#    cores = []
#    for i in range(1):
#        cores.append([str(i)])    #得到足够多的
#    in_core = open(corepath, 'r')  
#    cores[0] = in_core.readlines()
            
#递归拼接
#    for i in range(core_num):
#        tag = 'A' + str(i)
    for core in core_list:            
        for f in frag_list:
#           if reverse == 1:
#               f = f[::-1]                      
            compound = core.replace('*',f)
            print(compound)
            out.write(compound + '\n')
#                cores[i+1].append(new_core)     
#                print(cores[i+1])

          
#拼接完的分子写入out
#    for smi in cores[core_num]:
#        out.write(smi)
            


if __name__ == '__main__':
    BuildMolecule(in_core, in_frag, out)

    in_core.close()
    in_frag.close()
    out.close()




        
            


        


