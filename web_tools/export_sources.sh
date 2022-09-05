#!/bin/bash

# Export the source codes of AtChem, zip them and place them in /var/www/html/sources directory.
destdir=$PWD
cd /tmp
rev=$(svn info file:///home/mjp/scskb/svn_repo_atchem/trunk | grep '^Revision:') 
rev=${rev#Revision: } 
name="atchem_rev$rev"
svn export file:///home/mjp/scskb/svn_repo_atchem/trunk $name
echo "
	function svn_revision ()
		character(10) svn_revision
	    svn_revision = '$rev'
    end">> $name/svn_version.f
tar -cvf ${name}.tar $name
gzip ${name}.tar
mv ${name}.tar.gz /var/www/html/sources
rm -r $name
chmod a+r /var/www/html/sources/${name}.tar.gz

