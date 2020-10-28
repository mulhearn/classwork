#!/usr/bin/env python

import argparse
import re

MAIN_AUTHOR = "M. Mulhearn"

XML_START = r'<?xml version="1.0" encoding="UTF-8" ?><xml><records>'
XML_END   = r'</records></xml>'
XML_RECORD = '''
<record><ref-type name="Journal Article">17</ref-type>
<contributors><authors><author>MYAUTHORS</author></authors></contributors>
<titles><title>MYTITLE</title>
<secondary-title>MYJOURNAL</secondary-title></titles>
<pages>MYPAGES</pages>
<volume>MYVOLUME</volume>
<dates><year>MYYEAR</year></dates>
<urls><related-urls><url>MYURL</url></related-urls></urls>
</record>
'''

def clean_title(title):
    print("INFO:  cleaning title...")
    title =title.replace('$', '')
    title =title.replace('\\mathrm', '')
    title =title.replace('\\rm', '')
    title =title.replace('\\', '')
    title =title.replace('{', ' ')
    title =title.replace('}', ' ')
    return title

def clean_authors(authors):
    print("INFO:  cleaning authors...")
    m = re.search(r'\S+\s+(\S+)',MAIN_AUTHOR, re.S)
    last_name = m.group(1)
    if last_name in authors:
        return authors
    print("INFO:  author list does not contain ", last_name)

    m = re.search(r'^\s*(.*?),\s*(\S).*and others',authors, re.S)
    if (m != None):
        authors = str(m.group(2)) + ". " + str(m.group(1)) + ", " + MAIN_AUTHOR + ", and others"    
    return authors

def main(args):
    if (args.dryrun):
        print("INFO:  doing a dryrun only...")
    if (args.year):
        print("INFO: restricting output to year ", args.year)

    print("INFO:  starting bibtex conversion of", args.bib, "to", args.xml)

    if (not args.dryrun): 
        output = open(args.xml,"w")
        output.write(XML_START + "\n")
    
    articles = 0
    success = 0
    with open(args.bib) as input:
        contents = input.read()
        #print(contents)

        for m in re.finditer(r'@article.*?\n\s*}', contents, re.S):
            articles = articles+1
            print("INFO:  parsing article ", articles) 
            #print(m.group(0))
            mf = re.search(r'author\s*=\s*\"(.*?)\"', m.group(0), re.S)
            authors = mf.group(1)
            mf = re.search(r'title\s*=\s*\"{(.*?)}\"', m.group(0), re.S)
            title = mf.group(1)
            mf = re.search(r'journal\s*=\s*\"(.*?)\"', m.group(0), re.S)
            if (mf == None):
                #print("INFO: found non-journal article:  ")
                #print(m.group(0))
                continue
            journal = mf.group(1)
            mf = re.search(r'volume\s*=\s*\"(.*?)\"', m.group(0), re.S)
            volume = mf.group(1)
            mf = re.search(r'pages\s*=\s*\"(.*?)\"', m.group(0), re.S)
            pages = mf.group(1)
            mf = re.search(r'year\s*=\s*\"(.*?)\"', m.group(0), re.S)
            year = mf.group(1)
            if ((args.year) and (year != args.year)):
                print("INFO: skipping record from year ", year)
                continue
            mf = re.search(r'eprint\s*=\s*\"(.*?)\"', m.group(0), re.S)
            if (mf == None):
                url = ""
            else:
                url = "https://arxiv.org/abs/" + mf.group(1)

            title = clean_title(title)
            authors = clean_authors(authors)

            print("INFO:  authors:  ", authors)
            print("       title:    ", title) 
            print("       journal:   ", journal)
            print("       volume:    ", volume)
            print("       pages:     ", pages)
            print("       year:      ", year)

            record = XML_RECORD
            record =record.replace('MYAUTHORS', authors)
            record =record.replace('MYTITLE', title)            
            record =record.replace('MYYEAR', year)
            record =record.replace('MYVOLUME', volume)
            record =record.replace('MYPAGES', pages)
            record =record.replace('MYJOURNAL', journal)
            record =record.replace('MYURL', url)
            if (not args.dryrun):
                output.write(record + "\n")            
            success = success+1

    if (not args.dryrun): 
        output.write(XML_END + "\n")
        output.close()
            
    print("INFO: success parsing ", success, " journal articles from ", articles, " total articles.")
    

if __name__ == "__main__":
    example_text = '''examples:
    ...'''
    parser = argparse.ArgumentParser(description='Convert bibtex file to XML format used by UCD MIV.', epilog=example_text,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)    
    parser.add_argument('--dryrun',action="store_true", help="don't actually write anything.")
    parser.add_argument("bib", help="the bibtex file to convert")
    parser.add_argument("xml", help="the xml file to write")    
    parser.add_argument('--year', help='only output records from YEAR')
    args = parser.parse_args()
    main(args)
