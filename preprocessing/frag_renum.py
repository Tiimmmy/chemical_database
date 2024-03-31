from tqdm import tqdm
readDir = r"D:\CADD\Drug-likeness\smile\frag_sorted.smi"  #old
writeDir = r"D:\CADD\Drug-likeness\smile\frag_renum.smi" #new
f = open(readDir, "r")
outfile = open(writeDir, "w")

for frag in tqdm(f):
    frag_num = frag.replace('1', '9')
    frag_num2 = frag_num.replace('2','8')
    outfile.write(frag_num)
outfile.close()
print("success")
