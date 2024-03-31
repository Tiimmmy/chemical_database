corepath = r'D:\CADD\Drug-likeness\smile\core_refined.smi'
in_core = open(corepath, 'r')
outpath =  r'D:\CADD\Drug-likeness\smile\core_H.smi'
out_core = open(outpath, 'w')

def TagCore(in_core, out_core):
    core = in_core.read()
    tag_num = 0
    for c in core:
        if c == 'R':
            tag_num+= 1
    for i in range(1,tag_num):
        tag = '[R' + str(i) + ']'
        core = core.replace(tag, 'H', 1)

    out_core.write(core)


if __name__ == '__main__':
    TagCore(in_core,out_core)
    in_core.close()
    out_core.close()
