#!/bin/sh

#redirect output to stderr
exec 1>&2

#check that hooks are up-to-date
unset hooks_need_update
for filename in hooks/[^b]*.sh
do
    filename="${filename#hooks/}"
    diff "hooks/$filename" ".git/hooks/${filename%.sh}" 2> /dev/null >&2 || \
    { 
        echo "Warning: \"hooks/${filename}\" and \".git/hooks/${filename%.sh}\" differ!"
        hooks_need_update="x"
    }
done
if [ -n "$hooks_need_update" ]
then 
    echo "You may want to update your hooks. (Run hooks/bootstrap.sh again)"
    #Wait for a second, so that user can see this before making the commit message
    sleep 1
fi

#Look for undefined references in all *.log files
find -name '*.log' -exec grep '\(LaTeX Warning: There were undefined references.\|LaTeX Warning: There were multiply-defined labels.\)' '{}' \+ && { 
    echo "Undefined references and/or multiply-defined labels found in project. Commit rejected." 
    exit 1
}

#If everything goes well, accept the commit
exit 0
