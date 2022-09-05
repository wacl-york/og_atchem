SUBROUTINE TEMPERATURE(TEMP, H2O, TTIME)
! SUBROUTINE TO CALCULATE DIURNAL VARIATIONS IN TEMPERATURE
    DOUBLE PRECISION TEMP,TTIME, RH, H2O, SIN

    TEMP = 289.86 + 8.3*SIN((7.2722D-5*TTIME)-1.9635)
    temp = 298.00
    RH=23.0*SIN((7.2722D-5*TTIME)+1.1781)+66.5
    H2O=6.1078*DEXP(-1.0D+0*(597.3-0.57*(TEMP-273.16))*18.0/1.986*(1.0/TEMP-1.0/273.16))*10./(1.38D-16*TEMP)*RH

    RETURN
END
