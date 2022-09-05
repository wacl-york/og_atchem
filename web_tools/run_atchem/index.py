## import necessary modules

import subprocess
import sys
import re
import os
import cgi
import ntpath
import glob
import shutil
import pgtm
import facsmileToFortranMechanismConverter
from multiplot import table_of_plots

def index(req):
	return submit(req)
	
def submit(req):
	title = "Run AtChem code"
	content = pgtm.form() 
	dict={}
	dict.update(defaultvals())
	content = pgtm.sub_phdrs(content, dict)	
	return pgtm.page(title, content)

def run(req):
	## process data from form, run simulation and display results
	## display the job submission form if a form was not provided
	if not req.form.has_key('job'):
		return submit
	## process form data
	job = req.form.getfirst('job')
	## job name can only contain A-z, _ and numbers:
	job=re.sub("[^a-zA-Z0-9]+", "_", job)
	job=re.sub("_$", "", job)
	desc = req.form.getfirst('desc')
	model_par_list=("par_nb_steps", "par_step_size", "par_mxn_datapoints", "par_mxn_constrspec", 
		"par_rates_outstepsize", "par_start_time", "par_jacobian_outstepsize", "par_latitude", 
		"par_longitude", "par_day", "par_month", "par_year", "par_instrates_outstepsize")
	model_par_vals={}
	for par in model_par_list:
		model_par_vals[par] = req.form.getfirst(par)
	env_var_list = ("env_m", "env_temp", "env_pressure", "env_rh", "env_h2o", "env_dec", 
		"env_boundarylayerheight", "env_dilute", "env_jfac", "env_roofopen")
	env_var = {}
	for envar in env_var_list:
		env_var[envar] = req.form.getfirst(envar)
	## set paths
	scriptpath = __file__
	scriptdir = os.path.dirname(scriptpath) 
	atchem_input_dir = os.path.dirname(scriptdir)
	workdir_parent = '/tmp/atchem'
	workdir = ''
	jobdirname = job
	message = ''
	title = "AtChem on-line simulation results"
	dict={"SCRIPT_FILE": __file__}
	dict['JOB_DESC']=''
	if desc:
		dict['JOB_DESC'] = 'Description: ' + desc
	## prepare input/output directories
	try:
		## make sure that parent workdir for AtChem exists
		check_workdir(workdir_parent)
		## create unique id of the job, based on the last one
		ind = get_new_id()
		## create a temporary directory
		jobdirname = "%s_%03d" % (job, ind)
		dict["JOB_NAME"]=jobdirname
		title+=" -- job '%s'" % jobdirname
		workdir = "%s/%s" % (workdir_parent, jobdirname)
		failsafe_mkdir(workdir)
		## create input directories and copy the appropriate content inside
		for dir in ['modelConfiguration', ]:
			dirname =  workdir+'/'+dir
			failsafe_mkdir(dirname)
			for file in glob.glob(atchem_input_dir + '/' +  dir + '/*') :
				if os.path.isfile(file):
					failsafe_copy(file, dirname)
		## create empty input directory "speciesConstraints"
		failsafe_mkdir(workdir+'/'+'speciesConstraints')
		## create empty input directory "environmentalConstraints"
		failsafe_mkdir(workdir+'/'+'environmentalConstraints')
		## create empty directory "jobdirname_userinput" to contain original files
		userinputdir=workdir+'/'+jobdirname+'_userinput'
		failsafe_mkdir(userinputdir)
		## copy from atchem input directory all necessary files to build the atchem executable
		for file in glob.glob(atchem_input_dir + '/*.o') + glob.glob(atchem_input_dir + '/*.mod') + glob.glob(atchem_input_dir + '/*.f'):
			failsafe_copy(file, workdir, option='-p')
		files_to_copy =  ['Makefile', 'mechanism-rates.f']
		if os.path.isfile(atchem_input_dir+'/makefile.local'):
			files_to_copy.append('makefile.local')
		for file in files_to_copy:
			failsafe_copy(atchem_input_dir+'/'+file, workdir, option='-p')
		## upload mechanism file
		mech_orig_path=req.form['facfile'].filename
		mech_orig_name=anysys_basename(mech_orig_path)
		upload(req.form['facfile'], userinputdir, 'mechanism file', filetype='.fac')
		## upload initial concentrations file
		orig_path=req.form['icfile'].filename
		orig_name=anysys_basename(orig_path)
		upload(req.form['icfile'], userinputdir, 'initial concentrations file', filetype='.config')
		## copy initial concentrations file to modelConfiguration
		failsafe_copy(userinputdir+'/'+ orig_name, workdir+'/modelConfiguration/initialConcentrations.config')
		## fix the file - make sure there is "end -1\n" at the end
		append_to_file(workdir+'/modelConfiguration/initialConcentrations.config', "\nend -1\n")
		## upload zipped species constraint file(s) if provided:
		if req.form['zipcfile'].filename:
			orig_path=req.form['zipcfile'].filename
			orig_name=anysys_basename(orig_path)
			upload(req.form['zipcfile'], workdir+'/speciesConstraints', 'species constraints file(s)')
			## extract compressed constraints into separate files
			unpack_file(workdir+'/speciesConstraints',req.form['zipcfile'].filename, '-j')
			## save the original zip file
			failsafe_move(workdir+'/speciesConstraints/'+orig_name, userinputdir)
			## fix the files - make sure there is "end -1" everywhere
			for cf in glob.glob(workdir+'/speciesConstraints/*'):
				append_to_file(cf, "\nend    -1\n")
		## upload and unpack environmental constraints:
		if req.form['zipefile'].filename:
			orig_path=req.form['zipefile'].filename
			orig_name=anysys_basename(orig_path)
			upload(req.form['zipefile'], workdir+'/environmentalConstraints', 'environmental constraints file(s)')
			## extract compressed constraints into separate files
			unpack_file(workdir+'/environmentalConstraints',req.form['zipefile'].filename, '-j')
			## save the original zip file
			failsafe_move(workdir+'/environmentalConstraints/'+orig_name, userinputdir)
			## fix the files - make sure there is "end -1" everywhere
			for cf in glob.glob(workdir+'/environmentalConstraints/*'):
				append_to_file(cf, "\nend    -1\n")
			##  make sure all file names are in upper case
			for cf in glob.glob(workdir+'/environmentalConstraints/*'):
				cf_orig = os.path.basename(cf)
				cf_upper = cf_orig.upper()
				if cf_orig != cf_upper:
					failsafe_move(cf,workdir+'/environmentalConstraints/'+cf_upper)
		## upload concentrationOutput.config:
		if req.form['concentoutfile'].filename:
			orig_path=req.form['concentoutfile'].filename
			orig_name=anysys_basename(orig_path)
			upload(req.form['concentoutfile'], userinputdir, 'concentration output file')
			failsafe_copy(userinputdir+'/'+orig_name, workdir+'/modelConfiguration/concentrationOutput.config')
			## fix the file - make sure there is "\n" at the end
			append_to_file(workdir+'/modelConfiguration/concentrationOutput.config', "\nend\n")
		else:
			## if no file was provided, get species list from InitialConcentrations.config
			create_concentration_output_config(workdir)
		## upload photolysisRates.config:
		if req.form['photolysisratesfile'].filename:
			orig_path=req.form['photolysisratesfile'].filename
			orig_name=anysys_basename(orig_path)
			upload(req.form['photolysisratesfile'], userinputdir,'photolysis rates file')
			# get file type
			ftype = (os.path.splitext( orig_name ))[1]
			if ftype == '.rates':
				dest_name = 'photolysisRates.config'
			elif ftype == '.const':
				dest_name = 'photolysisConstants.config'
			else :
				raise Exception, "Error! Expected .rates or .const extension for photolysis rates file and found '%s' instead!" %ftype
			failsafe_copy(userinputdir+'/'+orig_name, workdir+'/modelConfiguration/' + dest_name)
			## fix the file - make sure there is "\n" at the end
			append_to_file(workdir+'/modelConfiguration/' + dest_name, "\n")

		## fix file modelConfiguration/constrainedSpecies.config so it will contain all the species uploaded
		fix_constrainedSpecies_config(workdir)	
		## fix file modelConfiguration/constrainedPhotoRates.config,
		## so it will contain all the environmental constraints uploaded
		fix_constrainedPhotoRates_config(workdir, env_var_list)	
		## convert the model file into Fortran files
		configdir = workdir+'/modelConfiguration'
		facsmileToFortranMechanismConverter.convert(userinputdir, configdir, mech_orig_name)
		## replace parameters by the ones sent through the form
		modify_model_parameters(configdir, model_par_vals)
		modify_environment_variables(configdir, env_var_list, env_var)
		save_in_file_end(configdir+'/JFacSpecies.config', req.form.getfirst('par_jfacspecies'))
		save_in_file_end(configdir+'/lossRatesOutput.config', req.form.getfirst('list_lossrates'))
		save_in_file_end(configdir+'/constrainedFixedSpecies.config', req.form.getfirst('list_fixedcons'))
		save_in_file_end(configdir+'/productionRatesOutput.config', req.form.getfirst('list_prodrates'))
		## recompile mechanism-rates.f and build atchem
		build_target(workdir, 'atchem')
		## create output directories
		failsafe_mkdir(workdir+'/modelOutput')
		failsafe_mkdir(workdir+'/instantaneousRates')
		## save job description and other parameters in job_description.txt file
		uname="System: "  + failsafe_syscall('uname -a') + "\n"
		gcc_ver = "Version of gcc: " + firstline(failsafe_syscall('gcc --version'))+ "\n"
		gfortran_ver = "Version of gfortran: " + firstline(failsafe_syscall('gfortran --version'))+ "\n"
		sys_info = uname + gcc_ver + gfortran_ver
		save_in_file(userinputdir+'/description.txt', 'Job '+jobdirname+'\n' + sys_info +  '\nDescription:\n'+desc+'\n')
	except Exception, e:
		err="Error preparing input/output data:\n%s\n" % e
		clean_ret=clean_up(workdir)
		if( clean_ret != 0):
			err += clean_ret;
		dict["ERR_STR"] = err
		content = pgtm.sub_phdrs(pgtm.run_error(), dict)
		return pgtm.page(title, content)
	## execute the program AtChem
	cmd = [workdir+'/atchem']
	try:
		p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=workdir)
		output = p.communicate()
		retval=p.wait()
	except OSError, e:
		err = "Execution of command '%s' failed! System error:\n%s" % (string.join(cmd, ' '), e)
		dict["ERR_STR"] = err
		content = pgtm.sub_phdrs(pgtm.run_error(), dict)
		return pgtm.page(title, content)
	## compress the output and copy to a download place
	try:
		resultdir = os.path.dirname(req.filename) +  "/atchem_results"
		resulturl = "atchem_results"		
		## compress job_userinput directory and move it to resultdir
		userinputurl  = "%s/%s_userinput.zip" % (resulturl, jobdirname )
		failsafe_zip_dir(userinputdir)
		failsafe_move(userinputdir+'.zip', resultdir)
		## create job_programinput directory, compress and move it to resultdir
		programinputdir  = "%s/%s_programinput" % (workdir, jobdirname )
		programinputurl  = "%s/%s_programinput.zip" % (resulturl, jobdirname )
		failsafe_mkdir(programinputdir)
		failsafe_move(workdir+'/modelConfiguration', programinputdir)
		failsafe_move(workdir+'/speciesConstraints', programinputdir)
		failsafe_move(workdir+'/environmentalConstraints', programinputdir)
		failsafe_zip_dir(programinputdir)
		failsafe_move(programinputdir+'.zip', resultdir)
		failsafe_clean_up(programinputdir)
		## create a list of remaining (output) files
		outfiles = []
		for f in ['modelOutput', 'instantaneousRates', 'atchem.out']:
			fp = workdir + '/' + f 
			if os.path.exists(fp):
				outfiles.append(fp)
		## create job_output directory, compress and move it to resultdir
		joboutputdir  = "%s/%s_output" % (workdir, jobdirname )
		joboutputurl  = "%s/%s_output.zip" % (resulturl, jobdirname )
		failsafe_mkdir(joboutputdir)
		for f in outfiles:
			failsafe_move(f, joboutputdir)
		## copy the output of the program into atchem.out file
		outfile = open(joboutputdir+'/atchem.out', "w")
		outfile.write(output[0])
		outfile.close()
		if(output[1]):
			errfile = open(joboutputdir+'/atchem.err', "w")
			errfile.write(output[1])
			errfile.close()
		failsafe_zip_dir(joboutputdir)
		failsafe_move(joboutputdir+'.zip', resultdir)
		## create the concentration plot
		ploterr = ""
		try:
			picturename = jobdirname+'_concentrations.png'
			plotsize = table_of_plots(joboutputdir+'/modelOutput/concentration.output', 
				resultdir+'/'+picturename,
				ncols=2, maxrows=10)
			if plotsize:
				dict["PLOTSURL"] = "%s/%s" % (resulturl, picturename )
				dict["PLOTSSIZEX"] = str(plotsize[0])
				dict["PLOTSSIZEY"] = str(plotsize[1])			
		except Exception, e:
			ploterr = "\n\n There was an error while preparing concentration plots.\n%s" % e
		## clean up the rest
		clean_up(workdir)
	except Exception, e:
		dict["ERR_STR"] = "Error while preparing output results for download.\n%s" % e
		content = pgtm.sub_phdrs(pgtm.run_error(), dict)
		return pgtm.page(title, content)
	## display the return value and the output
	dict["OUTDIR"] = joboutputurl
	dict["USERINDIR"] = userinputurl
	dict["PROGRAMINDIR"] = programinputurl
	dict["RETVAL"] = retval
	dict["STDERR"] = output[1]
	std_out=output[0]
	dict["STDOUT_ESC"]=''
	if(std_out):
		std_out=clean_output(std_out) + ploterr
		std_out_esc=cgi.escape(std_out)
		re_endl=re.compile('\n')
		dict["STDOUT_ESC"]=re_endl.sub( '<br>\n',std_out_esc)
	content = pgtm.sub_phdrs(pgtm.run_results(), dict)
	return pgtm.page(title, content)

###############################################################################	

def clean_up(workdir):
	if not(workdir): 
		return 0
	try:
		cleanup_retval = subprocess.call(["rm", '-rf', workdir])
	except  OSError, e:
		return "Cleaning of '%s' failed! System error: %s" % (workdir, e)
	return 0

def failsafe_mkdir(dirname):
	try:
		os.mkdir(dirname)
	except OSError, e:
		raise Exception, "Error! Failed to create directory '%s'.\nSystem error: '%s'." % (dirname, e)
	return 
	

def check_workdir(dirname):
	## check whether the directory exist
	if(os.path.exists(dirname)):
		if(os.path.isdir(dirname)):
			return 0
		else:
			raise Exception, "Error! Failed to create directory '%s'. Such file exists and is not a directory." % dirname
	## try to create the directory it if it doesn't exist
	failsafe_mkdir(dirname)
	return 0

def failsafe_zip_dir(dirname):
	## compress given directory with 'zip'
	name = os.path.basename(dirname)
	wdir = os.path.dirname(dirname)
	try:
		p = subprocess.Popen(['zip', '-r', name, name], stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=wdir)
		output = p.communicate()
		retval=p.wait()
	except OSError, e:
		raise Exception, "Error while compressing the output directory '%s'. System error: %s" % (dirname, e)
	if (retval != 0):
		err = "Error while compressing the output directories, command 'zip -r %s %s' returned %d." % (dirname, dirname, retval)
		if(output[0]):
			err+= "Command output:\n%s\n" % output[0]
		if(output[1]):
			err+= "Error output:\n%s\n" % output[1]
		raise Exception, err
	return 0

def failsafe_move(f1, f2):
	cmd = ['mv', f1, f2 ]
	try: 
		p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		output = p.communicate()
		retval=p.wait()
	except Exception, e:
		raise Exception, "Error! Failed moving '%s' to '%s'.\n%s" % (f1, f2, e)
	if retval !=0:
		err="Error! Command %s returned value %d!" % (cmd, retval)
		if(output[0]):
			err+= "\nCommand output:\n%s\n" % output[0]
		if(output[1]):
			err+= "\nError output:\n%s\n" % output[1]
		raise Exception, err
	return

def failsafe_clean_up(dirname):
	cmd = ['rm', '-rf', dirname ]
	try: 
		p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		output = p.communicate()
		retval=p.wait()
	except Exception, e:
		raise Exception, "Error! Failed removing '%s'.\n%s" % (dirname, e)
	if retval !=0:
		err="Error! Command 'rm -rf %s' returned value %d!" % (dirname, retval)
		if(output[0]):
			err+= "\nCommand output:\n%s\n" % output[0]
		if(output[1]):
			err+= "\nError output:\n%s\n" % output[1]
		raise Exception, err
	return

def failsafe_copy(f1, f2, option=''):
	if(option):
		cmd = ['cp', option, f1, f2]
	else:
		cmd = ['cp', f1, f2 ]
	try: 
		retval = subprocess.call(cmd)
	except OSError, e:
		raise Exception, "Error! Failed copying '%s' to '%s'.\nSystem error: '%s'. Aborting script." % (f1, f2, e)
	if retval != 0 :
		raise Exception, "Failed copying '%s' to '%s'.\nCopy returned value %d.\nCommand was \"%s\".\nAborting script." % (f1, f2, retval, cmd)
	return

def failsafe_syscall(command):
	# call a system command, returning just empty string if it fails
	# command is supposed to be a list, if it's a string, convert it.
	result=""
	try:
		if type(command) == str:
			command=command.split();
		proc = subprocess.Popen(command, stdout=subprocess.PIPE)
		(out, err) = proc.communicate()
		result=out.strip()
	except Exception, e:
		return ""
	return result

def firstline(s):
	ind=s.find("\n")
	s1 = s[0:ind]
	return s1.rstrip()
	
def build_target(workdir, target):
	# raise Exception, "files in workdir:\n%s" % "\n".join( glob.glob(workdir+'/*'))
	for cmd in [ ['make', target ] ]:
		try:
			p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=workdir)
			output = p.communicate()
			retval=p.wait()
		except Exception, e:
			raise Exception, "Error! Failed building target '%s'.\n%s" % (target, e)
		if (retval != 0):
			err = "Error while building target '%s', command %s returned %d." % (target, cmd, retval)
			if(output[0]):
				err+= "Command output:\n%s\n" % output[0]
			if(output[1]):
				err+= "Error output:\n%s\n" % output[1]
			raise Exception, err

def get_new_id():
	lastidfilename = os.path.dirname(__file__) +  "/../atchem_run.ind"
	try: 	
		lastidfile = open(lastidfilename, "r+")
		lastid = lastidfile.read()
		ind=int(lastid)+1
	except Exception, e:
		raise Exception, "Error! Failed reading indexing file %s.\n%s" % (lastidfilename, e)
	lastidfile.seek(0, 0)
	lastidfile.write("%d" % ind)
	lastidfile.truncate()
	lastidfile.close()
	return ind
	
def unpack_file(dir,filename, option=''):
	# strip leading path from file name:
	fname = anysys_basename(filename)
	# check whether the file is a zip file:
	ftype = (os.path.splitext( fname ))[1]
	if not (ftype == '.zip'):
		return
	for cmd in [ ['unzip', option, fname] ]:
		try:
			p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=dir)
			output = p.communicate()
			retval=p.wait()
		except Exception, e:
			raise Exception, "Error! Failed uncompressing file '%s'.\n%s" % (filename, e)
		if (retval != 0):
			err = "Error while uncompressing file '%s', command %s returned %d." % (filename, cmd, retval)
			if(output[0]):
				err+= "Command output:\n%s\n" % output[0]
			if(output[1]):
				err+= "Error output:\n%s\n" % output[1]
			raise Exception, err
	
def fix_constrainedSpecies_config(workdir):
	# read names of files in constrainedSpecies/ and write them in modelConfiguration/constrainedSpecies.config
	fnames = os.listdir(workdir+'/'+'speciesConstraints')
	csfile = open(workdir+'/'+'modelConfiguration/constrainedSpecies.config', "w")
	for fname in fnames:
		if re.match("[a-zA-Z0-9]+$", fname):
			csfile.write(fname+"\n")
	csfile.write("end\n")
	csfile.close()
		
def fix_constrainedPhotoRates_config(workdir, env_var_list):
	# read names of files in environmentalConstraints/ 
	# and write them in modelConfiguration/constrainedPhotoRates.config
	def getenvname(ev):
		return re.sub("env_", "", ev).upper()
	env_var_names = map(getenvname, env_var_list) 
	fnames = os.listdir(workdir+'/environmentalConstraints')
	csfile = open(workdir+'/modelConfiguration/constrainedPhotoRates.config', "w")
	for fname in fnames:
		if not fname in env_var_names:
			if re.match("[a-zA-Z0-9]+$", fname):
				csfile.write(fname+"\n")
	csfile.write("end\n")
	csfile.close()

def modify_model_parameters(dirname, par):
	filename=dirname+'/model.parameters'
	linetoedit={0: "par_nb_steps", 1: "par_step_size", 5: "par_mxn_datapoints", 6: "par_mxn_constrspec",
		7: "par_rates_outstepsize", 8: "par_start_time", 9: "par_jacobian_outstepsize", 
		10: "par_latitude", 11: "par_longitude", 12: "par_day", 13: "par_month", 14: "par_year", 
		15: "par_instrates_outstepsize"}
	##  check if all parameters were provided:
	for  nr in linetoedit:
		parname = linetoedit[nr]
		if not par[parname]:
			par_shortname = re.sub("par_", "", parname) 
			raise Exception, 'Parameter "%s" was not provided!' % par_shortname
	## modify model.parameters file
	try:
		fileh = open(filename, "r+")
		lines = fileh.readlines();
		re_firstword=re.compile('^\S+')
		for  nr in linetoedit:
			parname = linetoedit[nr]
			lines[nr] = re_firstword.sub( par[parname], lines[nr])
		fileh.seek(0,0)
		fileh.writelines(lines)
		fileh.truncate()
		fileh.close()
	except Exception, e:
		raise Exception, "Error! Failed substituting parameters in file '%s'.\n%s" % (filename, e)

def modify_environment_variables(dirname, evlist, evval):
	filename=dirname+'/environmentVariables.config'
	##  check if all variables were provided:
	nr = 0
	content = []
	for  ev in evlist:
		nr += 1
		var_name = re.sub("env_", "", ev).upper()
		if not evval[ev]:			
			raise Exception, 'Variable "%s" was not provided!' % var_name
		content.append ( str(nr) + "\t" + var_name + "\t" + evval[ev] + "\n" )
	content.append("end\tend\tend\n")
	## create file environmentVariables.config
	try:
		fileh = open(filename, "w")
		fileh.writelines(content)
		fileh.close()
	except Exception, e:
		raise Exception, "Error! Failed to create file '%s'.\n%s" % (filename, e)

def save_in_file_end(filename, data):
	# make sure last line contains "end"
	content = re.sub("\s+$", "", data)
	content += "\nend\n"
	try:
		fileh = open(filename, "w")
		fileh.write(content)
		fileh.close()
	except Exception, e:
		raise Exception, "Error! Failed to create file '%s'.\n%s" % (filename, e)

def save_in_file(filename, data):
	# save given string in a file
	try:
		fileh = open(filename, "w")
		fileh.write(data)
		fileh.close()
	except Exception, e:
		raise Exception, "Error! Failed to create file '%s'.\n%s" % (filename, e)

def append_to_file(filename, str):
	try:
		fileh = open(filename, "a")
		fileh.write(str)
		fileh.close()
	except Exception, e:
		raise Exception, "Error! Failed to fix/modify file '%s'.\n%s" % (filename, e)
	
def create_concentration_output_config(workdir):
	## read species from initialConcentrations.config 
	## and save them in concentrationOutput.config
	infile = workdir + '/modelConfiguration/initialConcentrations.config'
	outfile = workdir + '/modelConfiguration/concentrationOutput.config'
	try: 
		inf_h = open (infile, "r")
		lines = inf_h.readlines()
		inf_h.close()
		re_fw = re.compile('\S+')
		species = []
		for l in lines:
			res=re_fw.search(l)
			if res:
				fw = res.group(0)
				if not fw == 'end' :
					species.append(fw+"\n")
				else:
					species.append("end\n")
					break
		outf_h = open (outfile, "w")
		outf_h.writelines(species)
		outf_h.close()
	except Exception, e:
		raise Exception, "Error! Failed to create file '%s' based on file '%s'.\n%s" % (outfile, infile, e)
				
# uploading file sent through a form
def upload(fileitem, destdir, filedesc, filename='', filetype='', saveas=''):
	# Test if the file was uploaded
	if fileitem.filename:
		# strip leading path from file name to avoid directory traversal attacks
		fname = os.path.basename(fileitem.filename)
		fname = ntpath.basename(fname)
		# check that the name matches the optional argument filename:
		if filename:
			if fname != filename:
				raise Exception, 'Error! Expected %s to be named "%s" and got "%s" instead!' % (filedesc, filename, fname)
		# check that the file type matches the optional argument ftype
		if filetype:
			# get file type
			base,ftype = os.path.splitext( fname )
			# if ftype is '.txt' (e.g. from .config.txt), extract .txt and get ftype again
			if ftype == '.txt':
				txtftype =  (os.path.splitext( base ))[1]
				if txtftype:
					ftype=txtftype
			# if filetype doesn't start with dot, erase also dot from ftype
			if not re.match("\.",filetype):
				ftype = re.sub('^\.', '', ftype)
			if ftype.lower() != filetype.lower() :
				raise Exception, 'Error! Expected %s to have extension "%s" and got "%s" instead!' % (filedesc, filetype, ftype)
		if saveas:
			fname = saveas
		f = open(os.path.join(destdir, fname), 'wb', 10000)
		# Read the file in chunks
		for chunk in fbuffer(fileitem.file):
			f.write(chunk)
		f.close()
		return 
	else:
		raise Exception, 'Error! Failed to upload the %s.' % filedesc
		
def anysys_basename(filename):
	fname = os.path.basename(filename)
	fname = ntpath.basename(fname)
	return fname	

def clean_output(outstr):
	return re.sub('(time\s*=\s*\S+\s+time\s*=\s*\S+\s+)(time\s*=\s*\S+\s+)+(time\s*=\s*\S+\s+time\s*=\s*\S+\s+)',
	r'\1[...]\n\3', outstr) 
		
# Generator to buffer file chunks
def fbuffer(f, chunk_size=10000):
   while True:
      chunk = f.read(chunk_size)
      if not chunk: break
      yield chunk

def defaultvals():
	defvals = {"STEPSIZE":"900.0e+00"  , "NBSTEPS": "60", "JFACSPECIES": "", 
	"LOSS_RATES": "OH\nHO2\n", "PROD_RATES": "OH\nHO2\n",	
	"MXN_DATAPOINTS": "10000", "MXN_CONSTRSPEC": "50", "RATES_OUTSTEPSIZE": "3600", 
	"START_TIME": "3600.00e+00", "JACOBIAN_OUTSTEPSIZE": "108000", 
	"LATITUDE" : "52.943e00", "LONGITUDE": "0.00e+00", "DAY" : "19", "MONTH" : "11",
	"YEAR" : "2008", "INSTRATES_OUTSTEPSIZE": "900", "FIXEDCONS": ""}
	defvals_env = {"M": "2.60e+19", "TEMP": "281.95e+00", "PRESSURE": "NOTUSED",
		"RH": "NOTUSED", "H2O": "3.06e+17", "DEC": "0.28782328e+00", 
		"BOUNDARYLAYERHEIGHT": "NOTUSED", "DILUTE": "6.77E-6", "JFAC": "NOTUSED",
		"ROOFOPEN": "NOTUSED" }
	defvals_env_prep = {}
	def prepend_env(w): defvals_env_prep["ENV_"+w]=defvals_env[w]
	map(prepend_env, defvals_env)
	defvals.update(defvals_env_prep)
	defaultvals={}
	def prepend(w): defaultvals["DEFAULT_"+w]=defvals[w]
	map(prepend, defvals)
	return defaultvals

