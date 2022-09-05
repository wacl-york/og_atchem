#!/bin/bash

# create web application in the current directory
# (You need to set up Apache server with mod_python in order to use the webapp.)

od=$PWD
make makefile.local
make svnversion
chmod -R a+r .
chmod a+x . */
chmod a+rx web_tools/run_atchem/
chmod a+rx web_tools/run_atchem/*.py
chmod a+r web_tools/run_atchem/.htaccess 
ln -s web_tools/index.html index.html 
ln -s web_tools/atchem.css atchem.css 
if [[ ! -e atchem_run.ind ]] ; then
	if [[ -e ../atchem_run.ind ]] ; then
		ln -s ../atchem_run.ind atchem_run.ind
	else
		echo "0" > atchem_run.ind 
	fi
fi

mkdir run
chmod a+rx run
cd run
ln -s ../web_tools/run_atchem/index.py index.py 
ln -s ../web_tools/run_atchem/pgtm.py pgtm.py 
ln -s ../web_tools/run_atchem/.htaccess  .htaccess 
ln -s ../web_tools/run_atchem/facsmileToFortranMechanismConverter.py facsmileToFortranMechanismConverter.py 
ln -s ../web_tools/run_atchem/multiplot.py multiplot.py
ln -s ../web_tools/run_atchem/help.html help.html
chmod a+rw ../atchem_run.ind 
mkdir atchem_results
chmod a+rwx atchem_results

# remove write permissions, if stabilising the current version is required
if [[ "$1" == "-s" || "$1" == "--stabilise" ]] ; then
	cd $od
	chmod a-w *.f
fi
