#!/usr/bin/env python

import argparse
import re


MAIN_AUTHOR = "M. Mulhearn"

XML_START = r'<?xml version="1.0" encoding="UTF-8" ?><xml><records>'
XML_END   = r'</records></xml>'
XML_RECORD = '''
<record><ref-type name="Journal Article">17</ref-type>
<contributors><authors><author>%%MYAUTHORS%%</author></authors></contributors>
<titles><title>%%MYTITLE%%</title>
<secondary-title>%%MYJOURNAL%%</secondary-title></titles>
<pages>%%MYPAGES%%%%INDEX%%</pages>
<volume>%%MYVOLUME%%</volume>
<number>%%TAG%%</number>
<dates><year>%%MYYEAR%%</year></dates>
<urls><related-urls><url>%%MYURL%%</url></related-urls></urls>
</record>
'''

def check_fatal(x, reason):
    if (not x):
        print("ERROR:", reason)
        print("ERROR:  cowardly refusing to continue...\n")
        exit(0)

def extract_quoted_field(field, record, fatal=False):
    mf = re.search(field+r'\s*=\s*\"(.*?)\"', record, re.S)    
    if (not mf):
        if (fatal):
            print('ERROR:  could not parse required field "' + field + '" in record:  ')
            print(record)
            exit(0)
        return ""
    return mf.group(1)

def clean_title(title, args):
    mf = re.search(r'^\s*\{(.*)\}\s*$', title, re.S)    
    if (mf):
        title = mf.group(1)

    #print ("orig title: " + title)

    if (not args.no_latex):
        return title

    # remove math mode:
    title = re.sub(r'\$(.*?)\$', r'\1', title)

    # work-arounds:
    title = title.replace(r"sqrt{(}s)",r"sqrt{s}")

    title = re.sub(r'\\smash\s*\[\s*b\s*\]','',title)


    title = re.sub(r'\\overline\{(.*?)\}', r' \1-bar ', title)
    title = re.sub(r'\\bar\{(.*?)\}', r' \1-bar ', title)
    title = re.sub(r'\\bar\s+(\w+)\s+', r' \1-bar ', title)
    title = re.sub(r'\\bar\s+(\w+)\}', r' \1-bar} ', title)
    title = re.sub(r'\\bar\s+(\w+)\)', r' \1-bar) ', title)
    title = re.sub(r'\\bar\s+(\w+)$', r' \1-bar) ', title)

    title = re.sub(r'\\mathrm\s*\{\s*(.*?)\s*\}', r'\1', title)
    title = re.sub(r'\\rm\s*\{\s*(.*?)\s*\}', r'\1', title)
    title = re.sub(r'\\ensuremath\s*\{\s*(.*?)\s*\}', r'\1', title)
    title = re.sub(r'\\text\s*\{\s*(.*?)\s*\}', r'\1', title)

    title =title.replace(r'\,', ' ')
    title =title.replace(r'\;', ' ')

    title = title.replace(r'\rm','')


    title = re.sub(r'\\sqrt\s*\{\s*s\s*\}', r'sqrt(s)', title)
    title = re.sub(r'\\sqrt\s+s', r'sqrt(s)', title)
    title = re.sub(r'\\sqrt\s*\(\s*s\s*\)', r'sqrt(s)', title)
    title = re.sub(r'\\sqrt\s*\{\s*\(\s*s\s*\)\s*\}', r'sqrt(s)', title)


    title = re.sub(r'_\{(\S+?)\}', r'_\1', title)
    title = re.sub(r'\^\{(\S+?)\}', r'^\1', title)
    
    title = re.sub(r'\\sqrt\s*\{[{\s]*s[{}\s]*_+[{}\s]*N[{}\s]*N\}', r'sqrt(s_NN)', title)

    #title = re.sub(r'\{\s*(\S)\s*\}', r'\1', title)
    #title = re.sub(r'\{\s*(\S\S)\s*\}', r'\1', title)


    title =title.replace(r'\,', ' ')
    title =title.replace(r'\;', ' ')
    title =title.replace(r'\mu', ' mu')
    title =title.replace(r'\nu', ' nu')
    title =title.replace(r'\tau', ' tau')
    title =title.replace(r'\pm', '+-')
    title =title.replace(r'\mp', '-+')
    title =title.replace(r'\pi', ' pi')
    title =title.replace(r'\phi', ' phi')
    title =title.replace(r'\Upsilon', ' Upsilon')
    title =title.replace(r'\Lambda', ' Lambda')
    title =title.replace(r'\psi', ' psi')
    title =title.replace(r'\chi', ' chi')
    title =title.replace(r'\alpha', ' alpha')
    title =title.replace(r'\textendash{}',r'-')
    title =title.replace(r'\ell',r'l')
    title =title.replace(r'\rho',r'l')
    title =title.replace(r'\gamma',r'gamma')
    title =title.replace(r'\Delta',r'Delta')
    title =title.replace(r'\Gamma',r'Gamma')
    title =title.replace(r'\sin',r'sin')
    title =title.replace(r'\theta',r'theta')


    title = re.sub(r'\s*\\to\s*', r' to ', title)
    title = re.sub(r'\s*\\rightarrow\s*', r' to ', title)

    title = re.sub(r'mu\s+\+', r'mu+', title)
    title = re.sub(r'mu\s+\-', r'mu-', title)


    # loop over math expressions:
    #while(1):
    #    m = re.search(r'(.*?)\$(.*?)\$(.*)', title, re.S)
    #    if (m):
    #        math = m.group(2)
            #print("DEBUG:  MATH:  ", math)
    #        title = m.group(1) + math + m.group(3)
    #    else:
    #        break
    # cleanup spacing:
    title=title.replace("~"," ")
    title=title.replace(" '","' ")
    title=title.replace("-barH","-bar H")
    title=title.replace("J/ psi","J/psi")
    title = re.sub(r'\+\-', r'+- ', title)
    title = re.sub(r'\-\+', r'-+ ', title)
    title = re.sub(r'Te\s+V', r'TeV', title)
    title = re.sub(r'(\d)TeV', r'\1 TeV', title)
    title = re.sub(r'\s*sqrt\(\s*s\s*\)\s*=\s*', r' sqrt(s)=', title)

    # single space all white-space
    title = re.sub(r'\s+',' ',title)

    #print ("clean title: " + title)
    return title

def clean_authors(authors, args):
    if (not args.author):
        return
    m = re.search(r'\S+\s+(\S+)',args.author, re.S)
    last_name = m.group(1)
    if last_name in authors:
        return authors
    #print("INFO:  author list does not contain ", last_name)

    m = re.search(r'^\s*(.*?),\s*(\S).*and others',authors, re.S)
    if (m != None):
        authors = str(m.group(2)) + ". " + str(m.group(1)) + ", " + args.author + ", and others"    
    return authors

def main(args):
    
    print("INFO:  starting bibtex conversion of", args.bib, "to", args.xml)
    if (args.dry):
        print("INFO:  dry run:  will not write files.")
    if (args.no_latex):
        print("INFO:  will attempt to remove latex from title.")
    if (args.year):
        print("INFO:  restricting output to year ", args.year)
    #if (args.rejected):
    #    print("INFO:  writing rejected articles to rejected_REASON.bib")
    if (args.author):
        print('INFO:  target author is', args.author)
    
    articles = 0
    timely  = 0
    success = 0
    try:
        input = open(args.bib)
        contents = input.read()
    except:
        print("ERROR:  could not open bibtex file", args.bib)
        return

    #print(contents)

    records = []
    for m in re.finditer(r'@article.*?\n\s*}', contents, re.S):
        if ((args.max) and (success >= int(args.max))):
            break
        articles = articles+1
        print("INFO:  parsing article ", articles) 
        # require year field is present:
        year    = extract_quoted_field('year',  m.group(0), True)
        # quietly ignore non-target years if specified:
        if ((args.year) and (year != args.year)):
            #print("INFO: skipping record from year ", year)
            continue
        timely = timely+1

        # require author and title or give up
        authors = extract_quoted_field('author',  m.group(0), True)
        title   = extract_quoted_field('title',  m.group(0), True)

        # reject non-journal articles:
        journal = extract_quoted_field('journal', m.group(0), False)
        if (journal == ""):
            continue

        # require volume and pages or give up        
        volume = extract_quoted_field('volume',  m.group(0), True)
        pages  = extract_quoted_field('pages',  m.group(0), True)
        
        #mf = re.search(r'volume\s*=\s*\"(.*?)\"', m.group(0), re.S)
        #volume = mf.group(1)
        #mf = re.search(r'pages\s*=\s*\"(.*?)\"', m.group(0), re.S)
        #pages = mf.group(1)

        url = "NONE"
        archive = extract_quoted_field('archivePrefix',  m.group(0))
        if (archive == "arXiv"):
            eprint = extract_quoted_field('eprint',  m.group(0))
            if (eprint != ""):
                url = "https://arxiv.org/abs/" + eprint

        title = clean_title(title, args)
        authors = clean_authors(authors, args)

        print("INFO:  article:  ", articles)
        print("       authors:  ", authors)
        print("       title:    ", title) 
        print("       journal:   ", journal)
        print("       volume:    ", volume)
        print("       pages:     ", pages)
        print("       year:      ", year)
        print("       url:       ", url)

        record = XML_RECORD
        record =record.replace('%%MYAUTHORS%%', authors)
        record =record.replace('%%MYTITLE%%', title)            
        record =record.replace('%%MYYEAR%%', year)
        record =record.replace('%%MYVOLUME%%', volume)
        record =record.replace('%%MYPAGES%%', pages)
        record =record.replace('%%MYJOURNAL%%', journal)
        record =record.replace('%%MYURL%%', url)
        records.append(record)
        success = success+1
    # reverse the order since INSPIRES is most recent first:

    if (args.last):
        records[0] = records[0].replace('%%TAG%%', "*LAST*")
    records.reverse()

    # write the XML file header:
    if (not args.dry): 
        output = open(args.xml,"w")
        output.write(XML_START + "\n")

    index = 0;
    for record in records:
        index = index + 1
        if (args.new):
            record = record.replace('%%TAG%%', "*NEW*")
        else:
            record = record.replace('%%TAG%%', "")
        if (args.index):
            record = record.replace('%%INDEX%%', " ["+str(index)+"]")
        else:
            record = record.replace('%%INDEX%%', "")
        # write the record to XML file:
        if (not args.dry): 
            output.write(record + "\n")            

    # write the XML file tail:
    if (not args.dry): 
        output.write(XML_END + "\n")
        output.close()

    print("INFO: There were " + str(timely) + " articles in your time range from a total of " + str(articles))
    print("INFO: Successfully parsed " + str(success) + " out of " + str(timely) + " articles") 


    

if __name__ == "__main__":
    example_text = '''Complete Usage Example:

While it's not required, it's a good idea to use the --year option and
go year by year, checking the results.  It is alot easy to delete one
year worth of entries from MIV than three.

Suppose I had my last action in 2017 for a promotion in 2018.  My MIV
has journals in 2017, but is empty for 2018, 2019,and 2020.  Suppose I
have all my journals not already in MIV in the file
INSPIRE-CiteAll.bib by using SLAC Inspire.  It's important that this
not include any duplicates, because MIV does a mediocre job of finding
duplicates during upload.

For the year 2017, I'll have to append, so I use "--new" option:

   ./bib2miv.py INSPIRE-CiteAll.bib update_2017.xml --year 2017 --author "M. Mulhearn" --no_latex --new 

After uploading to MIV, I'll have to manually move the reference
marked *NEW* to the bottom of the list, and delete the tag
*NEW*.  This is because MIV import from XML shuffles the references,
presumably because the people that wrote MIV are idiots.

For the year 2018, and 2019, I don't have to use the "--new" option:

   ./bib2miv.py INSPIRE-CiteAll.bib update_2018.xml --year 2018 --author "M. Mulhearn"  --no_latex 
   ./bib2miv.py INSPIRE-CiteAll.bib update_2019.xml --year 2019 --author "M. Mulhearn"  --no_latex 

These can be uploaded to MIV with no manual adjustments needed.

For the year 2020, I use the "--last" option:

   ./bib2miv.py INSPIRE-CiteAll.bib update_2020.xml --year 2020 --author "M. Mulhearn"  --no_latex --last

After uploading to MIV, I move the reference tagged *LAST* to the end
of the list.  This will be a convenient reference when appending to this
year for a future action.
'''

    parser = argparse.ArgumentParser(description='Convert bibtex file to XML format used by UCD MIV.', epilog=example_text,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)    
    parser.add_argument('--dry',action="store_true", help="don't actually write any files.")
    #parser.add_argument('--rejected',action="store_true", help="write rejected bibtex records to rejected_REASON.bib.")
    parser.add_argument('--no_latex',action="store_true", help="remove LaTex from title")
    parser.add_argument("bib", help="the bibtex file to convert")
    parser.add_argument("xml", help="the xml file to write")    
    parser.add_argument('--year', help='only write files from YEAR')
    parser.add_argument('--max', help='stop after MAX records are parsed')
    parser.add_argument('--author', help='explicitly add AUTHOR when absent due to "and others", e.g. "M. Mulhearn"')
    parser.add_argument('--index',action="store_true", help="add index to page field")
    parser.add_argument('--new',action="store_true", help="add *NEW* to issue field, use when appending additional references to MIV in a year that already has references.")
    parser.add_argument('--last',action="store_true", help="add *LAST* to issue field for last record.  Use to move the last entry to the bottom of your MIV file, for easy reference when appening later.")
    args = parser.parse_args()
    main(args)
