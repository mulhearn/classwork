#!/bin/sh

#exit if any command fails
set -e

#check if %q conversion specifier is available
printf_q_available=""
#printf "%q" 2> /dev/null  >&2 && printf_q_available="y"
export printf_q_available

#cd to TLD of git repo from wherever we are
TLD="${0%/*}/.."
{ [ "$TLD" == "$0/.." ] && cd .. ; } || cd "$TLD"

#Check that there are scripts to copy over before doing anything
set hooks/[^b]*.sh
if [ "$1" == "hooks/[^b]*.sh" ] && [ "$#" -eq 1 ]
then 
    printf "No scripts found in hooks/ directory!\n"
    exit 1
fi

#Check that there are no oddly-named files, since malicious scripts can be hidden this way
set hooks/*[^a-zA-Z.-]*
if [ "$*" != 'hooks/*[^a-zA-Z.-]*' ]
then
    printf "Invalid file(s) found in hooks directory.\nInvalid files are as follows:\n"
    #Print invalid filenames. Uses printf "%q\n" if available, or od otherwise. od's output looks odd, but all the info is there
    if [ "$printf_q_available" == y ] ; then
        printf "%q\n" "$@"
    else
        printf "Output is in \`od\` format. Groups of numbers represent octal bytes of unprintable characters.\n"
        while [ $# -gt 0 ]
        do
            printf "%s" "$1" | od -A n -t c -v
            printf "\n"
            shift
        done
        set hooks/*[^a-zA-Z.-]*
    fi
    printf "Would you like to just delete these files? [y/n] "
    read prompt
    if [ "$prompt" == "y" ] || [ "$prompt" == "Y" ]
    then
        rm "$@"
        printf "Done! Moving on...\n"
    else
        exit 1
    fi
fi

#Check to make sure user really wants to run this script
printf "This will copy all of the scripts from hooks into .git/hooks.\nSpecifically, the following scripts will be copied:\n"
printf "%s\n" hooks/[^b]*.sh
printf "Is this okay? [y/n] "
read prompt
if [ "$prompt" != "y" ] && [ "$prompt" != "Y" ] ; then exit 1; fi

for hook in hooks/[^b]*.sh
do
    filename="${hook#hooks/}"
    filename="${filename%.sh}"
    #If the hook already exists, back it up. This clobbers any backups that may already exist
    if [ -f ".git/hooks/${filename}" ] ; then 
        printf "Backing up \".git/hooks/${filename}\" to \"hooks/.bak/${filename}.sh\"\n"
        cp ".git/hooks/${filename}" "hooks/.bak/${filename}.sh"
 
    fi
    cp "hooks/${filename}.sh" ".git/hooks/${filename}"
    chmod +x ".git/hooks/${filename}"
done

#Return to original directory (in case the script was sourced, for instance
cd - > /dev/null

printf "Success!\n"
