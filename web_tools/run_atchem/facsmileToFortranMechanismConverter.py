#!/usr/bin/python
import re
import os


def convert(inputdir=".", datadir='', inputfile='mechanism.fac', mechratesdir = ''):
    try:
        if not datadir:
            datadir = inputdir
        if not mechratesdir:
            mechratesdir = re.sub('/$', '', datadir)
            mechratesdir = re.sub('/[^/]+$', '', mechratesdir)
                     
        declared_rates = {}
        fmr = open(mechratesdir+'/mechanism-rates.f')
        fcont=fmr.readlines()
        fmr.close()
        re_decvar = re.compile('^\s*(integer|double)[^:]*::(.+)')
        for line in fcont:
            decvar_match = re_decvar.match(line)
            if(decvar_match):
                decvars_str = decvar_match.group(2)
                decvars_arr = decvars_str.split(',')
                for dr in decvars_arr:
                    declared_rates[dr.strip().upper()] = 1

        f = open(inputdir+'/'+inputfile)
        reac = open(datadir+'/mechanism.reactemp','w')
        prod = open(datadir+'/mechanism.prod','w')
        species = open(datadir+'/mechanism.species','w')
        mechRates = open(datadir+'/mechanism-rate-coefficients.ftemp','w')

        reac.write("numberOfSpecies numberOfReactions \n")
        s=f.read()
        # extract peroxy radicals
        regexp_ro2 = re.compile('^RO2\s*=\s*[^;]*;', re.MULTILINE)
        ro2_match = regexp_ro2.search(s)
        if ro2_match:
            ro2_str = ro2_match.group(0)
        else:
            raise Exception, "The mechanism file is missing RO2 sum"

        regexp_o2 = re.compile('^O2\s*=\s*[^;]*;', re.MULTILINE)
        o2_match = regexp_o2.search(s)
        if o2_match:
            o2_str = o2_match.group(0)
        else:
            o2_str='O2 = 0.2095*m'
        regexp_n2 = re.compile('^N2\s*=\s*[^;]*;', re.MULTILINE)
        n2_match = regexp_n2.search(s)
        if n2_match:
            n2_str = n2_match.group(0)

        else:
            n2_str='N2 = 0.7809*m'
        # extract generic rates
        rates_decl_file = open(datadir+'/mechanism-rate-declarations.f','w')
        regexp_vardef = re.compile(r'^(\s*([A-z0-9_]+)\s*=[^;]+);', re.MULTILINE)   
        arr_generic_rates = []
        reg_power = re.compile("@([-+]?\d*\.?\d+)") # hopefully more complex expressions will take care of the parentheses themselves
        for varline in regexp_vardef.finditer(s):
            genrate=varline.group(1)
            defined_var = varline.group(2)
            if re.match(defined_var.upper(), 'RO2'):
                continue
            if re.match(defined_var.upper(), 'O2'):
                continue
            if re.match(defined_var.upper(), 'N2'):
                continue
            genrate = reg_power.sub("**(\g<1>)", genrate)
	    genrate = genrate.replace("@","**")
            genrate = genrate.replace("<","(")
            genrate = genrate.replace(">",")")
            arr_generic_rates.append(genrate)
            if not declared_rates.has_key(defined_var.upper()):
                rates_decl_file.write("    double precision :: %s\n" % defined_var)
                declared_rates[defined_var.upper()] = 1
        rates_decl_file.close()
        b=[]
        speciesListCounter = 0
        speciesList = []
        rateConstants = []
        reactionNumber = 0
        reacFileCounter = 0
        facmech=[]

        # regular expression to recognize the equations
        # in FACSIMILE format
        refac = r'''
                ^%         # reactions begin with '%' (skip commented reactions)
                (.*?)      # rate coefficient
                (%(.*?))?  # optional rate coefficient of the backward reaction
                :          # delimiter rate coefficient/species
                (.*?)      # reactants
                =          # delimiter reactants/products
                (.*?)      # products
                ;          # reactions end with ';'
                '''

        # compile regular expression
        regexpfac = re.compile(refac, re.VERBOSE | re.MULTILINE | re.DOTALL)
        # apply regular expression to 's' string which contains the
        # chemical mechanism and find all the chemical equations
        for ifac in regexpfac.finditer(s):
            # extracts the rate coefficients of the forward (group 1) and
            # backward reactions (group 3), the reactants (group 4) and
            # the products (group 5) and delete the withespaces
            kf = re.sub(r"\s+", '', ifac.group(1))
            kb = ifac.group(3)
            r = re.sub(r"\s+", '', ifac.group(4))
            p = re.sub(r"\s+", '', ifac.group(5))

            # create list of reactants and products
            if r:
                react = r.split('+')
            else:
                react=[]
            if p:
                prod1 = p.split('+')
            else:
                prod1=[]

            # empty lists for the forward and backward reactions
            forweq = []
            backeq = []

            # if there is a backward reaction
            # delete whitespaces from backward rate coefficient
            if kb:
                kb =  re.sub(r"\s+", '', kb)

                # add to list for the forward reaction the rate coefficient
                # and the lists of reactants and products
                forweq.append(kf)
                forweq.append(react)
                forweq.append(prod1)

                # add to list for the backward  reaction the rate coefficient
                # and the lists of products and reactants
                backeq.append(kb)
                backeq.append(prod1)
                backeq.append(react)

                b.append(forweq)
                b.append(backeq)
                tm='% ' + kf + ' : ' + r + ' = ' + p + ';'
                facmech.append(tm)
                tm='% ' + kb + ' : ' + p + ' = ' + r + ';'
                facmech.append(tm)
            # if there is no backward reaction
            else:

                # add to list for the forward reaction the rate coefficient
                # and the lists of reactants and products
                forweq.append(kf)
                forweq.append(react)
                forweq.append(prod1)
                b.append(forweq)
                tm='% ' + kf + ' : ' + r + ' = ' + p + ';'
                facmech.append(tm)
        if len(facmech) == 0 :
            raise Exception, 'File does not contain a valid mechanism'
        
        for line in b:
            reactionNumber = reactionNumber + 1
            rateConstant = line[0]
            rateConstants.append(rateConstant)
           # print rateConstant
            
            reactants = line[1]
            products = line[2]
           # print "reactants = ",reactants
           # print "products = ",products
            
            if reactants:
            #	SEARCH FOR EXISTING REACTANTS
                i = 0
                speciesNumFound = 0
                reactantNums = []
                for x in reactants[:]:
                    j = 0
                    speciesNumFound = 0
                    #reactantNums = []
                    for y in speciesList:
                        if y == x.strip():
                            reactantNums.append(j+1)
                            speciesNumFound = 1
                    #        print "found: ",y,"j = ",j
                        j = j+1
                    
                    if speciesNumFound == 0:
                        speciesList.append(x.strip())
                        speciesListCounter = speciesListCounter + 1
                        reactantNums.append(speciesListCounter)
                      #  print "adding ", x.strip(), " to speciesList" 
                    i=i+1
    #		WRITE TO MECH.REAC FILE THE REACTANTS		
                for z in reactantNums:
                    temp = str(reactionNumber)+' '+ str(z)
                    reac.write(temp)
                    reac.write('\n')
            
            if products:
                #	SEARCH FOR EXISTING REACTANTS
                i = 0
                speciesNumFound = 0
                productNums = []
                for x in products[:]:
                    j = 0
                    speciesNumFound = 0
                    #productNums = []
                    for y in speciesList:
                        if y == x.strip():
                            productNums.append(j+1)
                            speciesNumFound = 1
                #            print "found: ",y,"j = ",j
                        j = j+1
                   # print "speciesNumFound = ",speciesNumFound
                    if speciesNumFound == 0:
                        speciesList.append(x.strip())
                        speciesListCounter = speciesListCounter + 1
                        productNums.append(speciesListCounter)
                #        print "adding ", x.strip(), " to speciesList" 
                    i=i+1
        #		WRITE TO MECH.REAC FILE THE REACTANTS		
                for z in productNums:
                    temp = str(reactionNumber)+' '+ str(z)
                    prod.write(temp)
                    prod.write('\n')

        # MARK END OF FILE WITH ZEROS
        reac.write("0	0	0	0 \n")	
        prod.write("0	0	0	0 \n")	
        size = len(speciesList)
        st =  str(size)+ " " +str(reactionNumber) + " numberOfSpecies numberOfReactions"
        reac.write(st)
        reac.close()

        # REARRANGE MECHANISM.REAC FORMAT TO MAKE IT READABLE BY THE MODEL
        reac1 = open(datadir+'/mechanism.reactemp')
        reacFin = open(datadir+'/mechanism.reac','w')
        st=reac1.readlines()
        reacFin.write(st[len(st)-1])

        counter = 0
        for line in st:
            counter = counter + 1
            if counter < len(st):
                reacFin.write(line)
        reac.close()
        reacFin.close()
        #	WRITE OUT TO MECH.SPECIES FILE	
        i = 1
        for x in speciesList:
            st = str(i) + ' ' + str(x)
            species.write(st)
            species.write('\n')
            i = i + 1 
                
        #	WRITE OUT RATE COEFFICIENTS
        i = 1
        counter = 0
	re_power = re.compile("@([-+]?\d*\.?\d+)") # hopefully more complex expressions will take care of the parentheses themselves
        for x in rateConstants:
            string = re_power.sub("**(\g<1>)", x)
	    string = string.replace("@","**")
            string = string.replace("<","(")
            string = string.replace(">",")")
            tm=facmech[counter]
            st = "	p("+str(i)+") = " + string + "  !" + tm
            mechRates.write(st)
            mechRates.write('\n')
            i = i + 1 
            counter =  counter + 1
                
        mechRates.close()

        fortranFile = open(datadir+'/mechanism-rate-coefficients.f','w')

        # Process the RO2 sum
	ro2_str=ro2_str[:-1]
        l = ro2_str.split("=")[1]
        strArray = l.split("+")
        ro2List = []
	for x in strArray:
            if not x=='':
                x = x.strip()
                ro2List.append(x)

	# loop over RO2 to get species numbers and write
	extraSubFile = open(datadir+'/extraOutputSubroutines.f','w')
        counter = 0
        speciesFound = 0
	extraSubFile.write("subroutine ro2sum(ro2, y)\n")
	extraSubFile.write("double precision:: ro2\n")
	extraSubFile.write("double precision, intent(in) :: y(*)\n")
        extraSubFile.write("    ro2 = 0.00e+00\n")
        for ro2i in ro2List:
            speciesFound = 0
            counter = 0
            for y in speciesList:
                if(ro2i.strip()==y.strip()):
                    speciesNumber = counter + 1
                    speciesFound = 1
                counter = counter + 1
            if (speciesFound == 1):
                st = "\tro2 = ro2 + y("+str(speciesNumber)+")!"+ro2i.strip() +"\n"
                extraSubFile.write(st)
            elif (speciesFound == 0):
                extraSubFile.write("\t ! Warning! RO2 not in mechanism: " )
                extraSubFile.write(ro2i)
                extraSubFile.write("\n")
	extraSubFile.write("end subroutine ro2sum\n")
        extraSubFile.write('\n\n')	
	
	extraSubFile.write("""
subroutine atmosphere(O2, N2, m)
double precision:: O2, N2, m
    %s
    %s
END subroutine atmosphere
""" % ( o2_str, n2_str))

        # Process NOY files, if provided		
        if os.path.exists('./NOY.fac') :
            # DO NOY SUM
            NOYFac = open(datadir+'/NOY.fac')
            NOY = NOYFac.readlines()
            counter = 0
            NOYList = []
            for n in NOY:
                counter = counter + 1
                if (counter==1):
                    strArray = n.split("=")
                    n = strArray[1]
                strArray = n.split("+")
              #  print strArray
                for x in strArray[:]:
                    x = x.strip()
                    if(x==''):
                        print "doing nothing"
                    else:
                        print x
                        NOYList.append(x)	
            # loop over NOY to get species numbers and write
            counter = 0
            speciesFound = 0
            fortranFile.write("\tNOY = 0.00e+00\n")
            for NOYi in NOYList:
                speciesFound = 0
             #   print "NOYi: " + NOYi
                counter = 0
                for y in speciesList:
                    if(NOYi.strip()==y.strip()):
                        speciesNumber = counter + 1
                        speciesFound = 1
                    counter = counter + 1
                if (speciesFound == 1):
                    st = "\tNOY = NOY + y("+str(speciesNumber)+")!"+NOYi.strip() +"\n"
                    fortranFile.write(st)
                elif (speciesFound == 0):
                    fortranFile.write("\t !error NOY not in mechanism: " )
                    fortranFile.write(NOYi)
                    fortranFile.write("\n")
            fortranFile.write('\n\n')	
            
        # include generic rates declarations
        fortranFile.write("\n".join(arr_generic_rates))
	fortranFile.write("\n")
        
        # Combine mechanism rates and RO2 / NOY sum files
        rates = open(datadir+'/mechanism-rate-coefficients.ftemp')
        rs = rates.readlines()

        for r in rs:
            fortranFile.write(r)

        reac.close()
        prod.close()
        species.close()
                
    except Exception, e:
        raise Exception, 'Cannot convert mechanism file. Error: %s.' % e
    os.remove(datadir+'/mechanism.reactemp')
    os.remove(datadir+'/mechanism-rate-coefficients.ftemp')

if __name__ == "__main__":
    convert()
