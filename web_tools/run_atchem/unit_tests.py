#!/usr/bin/python
import unittest
import pgtm


class Test_sub_phdrs(unittest.TestCase):
	methodName='runTest'
	s1=""" AAA """
	s2=""" BBB """
	d1="MILLENIUM"
	v1="1000"
	p1="PHDR_"+d1
	d2="BARBRA"
	v2="Streissand"
	p2="PHDR_"+d2
	pw="PHDR_FALSE"
	ob="PHDR_OPT_BEG"
	oe="PHDR_OPT_END"
	# expected input/output values:
	case_no_phdrs = ((s1, s1), (s2, s2), (s1+s2, s1+s2))
	case_phdrs = ((p1, v1), (p2, v2), (s1+p1+s2, s1+v1+s2), (s1+p1+s2+p2+s1+p1, s1+v1+s2+v2+s1+v1))
	case_opt_nophdrs = ((s1+ob+s1+oe+s2, s1+s2), (s1+ob+s1+pw+s2+oe+s2, s1+s2))
	case_opt_phdrs = ((s1+ob+s1+p1+s2+oe+s2, s1+s1+v1+s2+s2),)
	case_long = ((s1+p1+s2+p2+s1+ob+s1+p1+s2+p2+s1+oe+s2+p1+s1+p2,
		     s1+v1+s2+v2+s1+s1+v1+s2+v2+s1+s2+v1+s1+v2), (s1, s1) )
	## input that should produce assertion:
	wrong_inp=(s1+pw+s2, s1+ob+s1+p1+s2+p2+s1+pw+oe)
	dict={d1: v1, d2: v2}
	def runForCase(self, inout):
		for inp, out in inout:
			result = pgtm.sub_phdrs(inp,self.dict)
			self.assertEqual(out, result) 
	def test_simplest(self):
		inp="PHDR_CAR and PHDR_FISH"
		exp_out="Vw and Shark"
		dic={'CAR': 'Vw', 'FISH': 'Shark'}
		result = pgtm.sub_phdrs(inp,dic)
		self.assertEqual(exp_out, result) 
	def test_nophdrs(self):
		"""string with no placeholders should be unchanged """
		self.runForCase(self.case_no_phdrs)
	def test_phdrs(self):
		"""placeholders should be substituted by values"""
		self.runForCase(self.case_phdrs)
	def test_opt_nophdrs(self):
		"""optional block with no valid placeholder inside should be removed"""
		self.runForCase(self.case_opt_nophdrs)
	def test_opt_phdrs(self):
		"""valid placeholder inside of optional block should be replaced """
		self.runForCase(self.case_opt_phdrs)
	def test_long(self):		
		"""test a long case, with placeholders inside and inside of the optional block"""
		self.runForCase(self.case_long)
	def test_wrong_inp(self):
		"""invalid placeholder should raise exception"""
		for inp in self.wrong_inp:
			self.assertRaises(KeyError, pgtm.sub_phdrs, inp, self.dict)
			
if __name__ == '__main__':
	unittest.main()