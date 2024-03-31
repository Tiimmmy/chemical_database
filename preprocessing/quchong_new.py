# import shutil

from tqdm import tqdm
a=0
readDir = r"D:\CADD\Drug-likeness\smile\tag_r.smi"  #old
writeDir = r"D:\CADD\Drug-likeness\smile\total_unique.smi" #new
# txtDir = "/home/Administrator/Desktop/１"
lines_seen = set() #创建一个无序不重复元素集
outfile = open(writeDir, "w")
f = open(readDir, "r")
#i=1
for line in tqdm(f):
  if line not in lines_seen:
    strout = line.strip('\n')
    outfile.write(strout + '\n')
    lines_seen.add(line)
#    i = i + 1

outfile.close()
print("success")
