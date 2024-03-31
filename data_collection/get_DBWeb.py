from selenium import webdriver
import time
from lxml import etree
import xlrd
import pandas as pd

def get_url(in_path, sheetnum, name):
    data = xlrd.open_workbook(in_path)
    table = data.sheets()[sheetnum]
    nor = table.nrows
    nol = table.ncols
    
    for i in range(1,nor):
        name.append(table.cell_value(i,0))
        key_world = table.cell_value(i,0)
        #key_world = "Loteprednol"
        url = "https://cn.bing.com/search?q=" + key_world + " metabolite&ensearch=1"
        yield url

def metabolism(r,meta_list):
    html = etree.HTML(r)
    #f = html.xpath("//div")
    #f = html.xpath("//strong")
    f = html.xpath("//div[@class='rwrl rwrl_pri rwrl_padref']/text()")
    meta_list.append(''.join(f))
    print(meta_list)



if __name__ == '__main__':
    opt = webdriver.ChromeOptions()
    opt.set_headless()
    driver = webdriver.Chrome(options=opt)
    in_path = r"D:\OldDrug\NoM.xlsx"
    out_path = r"D:\OldDrug\MInfo_20002.xlsx"
    name=[]
    meta_list=[]
    for url in get_url(in_path, 4, name):
        driver.get(url)
        time.sleep(7)
    #print(driver.page_source)
        r = driver.page_source
    
        metabolism(r,meta_list)
        MList=zip(name,meta_list)
        df = pd.DataFrame(MList, columns=['name', 'metabolism'])
        df.to_excel(out_path, index=False)






'''
for i in f:
    print(i.text)
'''

'''
print("waiting response...")
wait = WebDriverWait(browser, 10)
wait.until(EC.presence_of_element_located((By.CLASS_NAME, "grid")))
'''
#print("geting web data...")

#print(driver.page_source.encode('gbk','ignore'))

#print(soup)
#browser.close()
