import re

def version():
	return "1.5"

def sub_phdrs(templ, dict):
	## remove lines with PHDR_OPT if optional 
	parts = re.split('PHDR_OPT_BEG|PHDR_OPT_END', templ)
	rvar = re.compile("PHDR_((\w|_)+)")
	def checkopt(fragm):
		## check if the first placeholder is valid
		varm = rvar.search(fragm)
		if varm:
			var=varm.group(1)
			if dict.get(var, ""):
				return fragm
		return ""
	if len(parts) > 1:
		parts[1::2] = map(checkopt,parts[1::2])
	string = "".join(parts)
	## substitute placeholders of type PHDR_* with values from dictionnary
	def lookup(match):
		var = match.group(1)
		# return dict.get(var, '')
		return str(dict.get(var,''))
	return rvar.sub(lookup, string)

def makeradios(predefdirs, templ):
	global count
	count = 0
	def makeradio(d):
		global count
		checked=''
		if count == 0:
			checked='checked'
		count=count+1
		return templ % (d, d, predefdirs[d], checked)
	return "\n".join(map(makeradio, predefdirs))

def form():
	return """\
Please set the parameters and press "Run" button.
Check the <a href="help.html">help</a> for detailed explanation.
<form action="run.py" name=form1 enctype="multipart/form-data" method="post">
<p class="short">
<label for="job">job name</label>
<input name="job" class="short" id="job" type="text">
</p>
<p class="long">
<label for="desc">description</label>
<textarea cols="50" rows="2" name="desc" id="desc"></textarea>
<h3>Data files</h3>
<p class="long">
<label for="facfile">mechanism file*</label>
<input name="facfile" id="facfile" type="file">
</p>
<p class="long">
<label for="icfile">initial concentration file*</label>
<input name="icfile" id="icfile" type="file">
</p>
<p class="long">
<label for="zipcfile">species constraints (zipped)</label>
<input name="zipcfile" id="zipcfile" type="file">
</p>
<p class="long">
<label for="zipefile">environmental constraints (zipped)</label>
<input name="zipefile" id="zipefile" type="file">
</p>
<p class="long">
<label for="concentoutfile">concentration output</label>
<input name="concentoutfile" id="concentoutfile" type="file">
</p>
<p class="long">
<label for="photolysisratesfile">photolysis rates</label>
<input name="photolysisratesfile" id="photolysisratesfile" type="file">
</p>
<p>*mandatory.</P>
<h3>Environment variables</h3>
<p class="short">
	<label for="env_m">M</label>
	<input name="env_m" class="short" id="env_m" value="PHDR_DEFAULT_ENV_M" type="text"  onblur="this.value=this.value.toUpperCase()">
</p>
<p class="short">
	<label for="env_temp">TEMP</label>
	<input name="env_temp" class="short" id="env_temp" value="PHDR_DEFAULT_ENV_TEMP" type="text"   onblur="this.value=this.value.toUpperCase()"  >
</p>
<p class="short">
	<label for="env_pressure">PRESSURE</label>
	<input name="env_pressure" class="short" id="env_pressure" value="PHDR_DEFAULT_ENV_PRESSURE" type="text"   onblur="this.value=this.value.toUpperCase()">
</p>
<p class="short">
	<label for="env_rh">RH</label>
	<input name="env_rh" class="short" id="env_rh" value="PHDR_DEFAULT_ENV_RH" type="text"   onblur="this.value=this.value.toUpperCase()">
</p>
<p class="short">
	<label for="env_h2o">H2O</label>
	<input name="env_h2o" class="short" id="env_h2o" value="PHDR_DEFAULT_ENV_H2O" type="text"   onblur="this.value=this.value.toUpperCase()">
</p>
<p class="short">
	<label for="env_dec">DEC</label>
	<input name="env_dec" class="short" id="env_dec" value="PHDR_DEFAULT_ENV_DEC" type="text"   onblur="this.value=this.value.toUpperCase()">
</p>
<p class="short">
	<label for="env_boundarylayerheight">BOUNDARYLAYERHEIGHT</label>
	<input name="env_boundarylayerheight" class="short" id="env_boundarylayerheight" value="PHDR_DEFAULT_ENV_BOUNDARYLAYERHEIGHT" type="text"   onblur="this.value=this.value.toUpperCase()">
</p>
<p class="short">
	<label for="env_dilute">DILUTE</label>
	<input name="env_dilute" class="short" id="env_dilute" value="PHDR_DEFAULT_ENV_DILUTE" type="text"   onblur="this.value=this.value.toUpperCase()">
</p>
<p class="short">
	<label for="env_jfac">JFAC</label>
	<input name="env_jfac" class="short" id="env_jfac" value="PHDR_DEFAULT_ENV_JFAC" type="text"   onblur="this.value=this.value.toUpperCase()">
</p>
<p class="short">
	<label for="env_roofopen">ROOFOPEN</label>
	<input name="env_roofopen" class="short" id="env_roofopen" value="PHDR_DEFAULT_ENV_ROOFOPEN" type="text"   onblur="this.value=this.value.toUpperCase()">
</p>
<h3>Model parameters</h3>
<p class="short">
	<label for="par_nb_steps">number of steps</label>
	<input name="par_nb_steps" class="short" id="par_nb_steps" value="PHDR_DEFAULT_NBSTEPS" type="text"\
	onChange="document.form1.par_jacobian_outstepsize.value=document.form1.par_step_size.value*document.form1.par_nb_steps.value*2;" 
	>
</p>
<p class="short">
	<label for="par_step_size">step size (seconds)</label>
	<input name="par_step_size" class="short" id="par_step_size" value="PHDR_DEFAULT_STEPSIZE" type="text"
	onChange="document.form1.par_jacobian_outstepsize.value=document.form1.par_step_size.value*document.form1.par_nb_steps.value*2;" 
	>
</p>
<p class="short">
	<label for="par_mxn_datapoints">max. nr of lines in constraints files</label>
	<input name="par_mxn_datapoints" class="short" id="par_mxn_datapoints" value="PHDR_DEFAULT_MXN_DATAPOINTS" type="text">
</p>
<p class="short">
	<label for="par_mxn_constrspec">max. nr of constrained species</label>
	<input name="par_mxn_constrspec" class="short" id="par_mxn_constrspec" value="PHDR_DEFAULT_MXN_CONSTRSPEC" type="text">
</p>
<p class="short">
	<label for="par_rates_outstepsize">rates output step size</label>
	<input name="par_rates_outstepsize" class="short" id="par_rates_outstepsize" value="PHDR_DEFAULT_RATES_OUTSTEPSIZE" type="text">
</p>
<p class="short">
	<label for="par_start_time">model start time</label>
	<input name="par_start_time" class="short" id="par_start_time" value="PHDR_DEFAULT_START_TIME" type="text">
</p>
<p class="short">
	<label for="par_jacobian_outstepsize">Jacobian output step size</label>
	<input name="par_jacobian_outstepsize" class="short" id="par_jacobian_outstepsize" value="PHDR_DEFAULT_JACOBIAN_OUTSTEPSIZE" type="text">
</p>
<p class="short">
	<label for="par_latitude">latitude</label>
	<input name="par_latitude" class="short" id="par_latitude" value="PHDR_DEFAULT_LATITUDE" type="text">
</p>
<p class="short">
	<label for="par_longitude">longitude</label>
	<input name="par_longitude" class="short" id="par_longitude" value="PHDR_DEFAULT_LONGITUDE" type="text">
</p>
<p class="short">
	<label for="par_day">day</label>
	<input name="par_day" class="short" id="par_day" value="PHDR_DEFAULT_DAY" type="text">
</p>
<p class="short">
	<label for="par_month">month</label>
	<input name="par_month" class="short" id="par_month" value="PHDR_DEFAULT_MONTH" type="text">
</p>
<p class="short">
	<label for="par_year">year</label>
	<input name="par_year" class="short" id="par_year" value="PHDR_DEFAULT_YEAR" type="text">
</p>
<p class="short">
	<label for="par_instrates_outstepsize">inst. rates output step size</label>
	<input name="par_instrates_outstepsize" class="short" id="par_instrates_outstepsize" value="PHDR_DEFAULT_INSTRATES_OUTSTEPSIZE" type="text">
</p>
<h3>Other</h3>
<p class="short">
	<label for="par_jfacspecies">JFAC species</label> <!-- some more clear label here? -->
	<input name="par_jfacspecies"  class="short" id="par_jfacspecies" value="PHDR_DEFAULT_JFACSPECIES" type="text"	>
</p>
<p class="short">
	<label for="list_fixedcons">fixed-concentration species</label>
	<textarea name="list_fixedcons" id="list_fixedcons"	>PHDR_DEFAULT_FIXEDCONS</textarea>
</p>

<p class="short">
	<label for="list_lossrates">loss rates output</label> <!-- some more clear label here? -->
	<textarea name="list_lossrates" id="list_lossrates"
		onChange="document.form1.list_prodrates.value=document.form1.list_lossrates.value;"
	>PHDR_DEFAULT_LOSS_RATES</textarea>
</p>
<p class="short">
	<label for="list_prodrates">production rates output</label> <!-- some more clear label here? -->
	<textarea name="list_prodrates" id="list_prodrates">PHDR_DEFAULT_PROD_RATES</textarea>
</p>

<p class="submit"><input class="short" value="Run" type="submit"></p>
</form>
<div class="shadow" id="shadow">
<div class="output" id="output">
</div>
</div>
"""

def run_error():
	return """\
<div class="right">&#x2022;&nbsp;<a class="homelink" href="../..">Home page of AtChem on-line project</a>&nbsp;&#x2022;&nbsp;<a class="homelink" href="../">Submit another job</a>&nbsp;&#x2022;&nbsp;</div>
<H2>Error!</H2>
An error ocurred during job PHDR_JOB_NAME while executing the script PHDR_SCRIPT_FILE.<BR>
<pre>PHDR_ERR_STR</pre>"""

def run_results():
	return """\
<div class="right">&#x2022;&nbsp;<a class="homelink" href="../..">Home page of AtChem on-line project</a>&nbsp;&#x2022;&nbsp;<a class="homelink" href="../">Submit another job</a>&nbsp;&#x2022;&nbsp;</div>
<h1>Execution results for job 'PHDR_JOB_NAME'</h1>
<div id="container">
<div id=datainfo>PHDR_JOB_DESC</div>
<P class="important">Program executed and returned value PHDR_RETVAL.</P>
<div class="uploads">
  <P><A HREF="PHDR_OUTDIR">download output files</A></P>
  <p><a href="PHDR_USERINDIR">download input files</a></p>
<!--  <p><a href="PHDR_PROGRAMINDIR">download program input files</a></p>  -->
</div>
PHDR_OPT_BEG<P class="important">ERROR OUTPUT:</P><pre>PHDR_STDERR</pre>PHDR_OPT_END
<P class="important">PROGRAM OUTPUT</P>\n<div id="pre">PHDR_STDOUT_ESC</div>
PHDR_OPT_BEG<P class ="important">CONCENTRATIONS</P>\n<img src="PHDR_PLOTSURL" alt="Concentration plots" width="PHDR_PLOTSSIZEX" height="PHDR_PLOTSSIZEY">PHDR_OPT_END
</div>
"""

def page(title='', content=''):
	str = """\
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">
<html>
<head>
<meta http-equiv="content-type" content="text/html; charset=UTF-8">
  <link rel="stylesheet" type="text/css" href="../atchem.css">
  <title>%s</title>
</head>
<body onLoad="init();">
<div class="titlebar">
<h1>AtChem on-line</h1>
<p id="version">version %s</p>
</div>
<div id="container">
%s
</div>
<div class="homelink"><a href="https://atchem.leeds.ac.uk/">Home page of AtChem on-line project</a></div>
</body></html>
"""
	# return sub_phdrs(str, {"TITLE" : title, "CONTENT" : content})
	return str % (title, version(), content)
