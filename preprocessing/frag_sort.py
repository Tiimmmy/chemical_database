from tqdm import tqdm
a=0
readDir = r"D:\CADD\Drug-likeness\smile\frags.smi"  #old
writeDir = r"D:\CADD\Drug-likeness\smile\frag_sorted.smi" #new
f = open(readDir, "r")
outfile = open(writeDir, "w")

for line in tqdm(f):
    if len(line) <= 15:
        outfile.write(line)
outfile.close()
print("success")
