# Demostració entrevista

Aquest fitxer proporciona una possible seqüència d'ordres per a la demostració del projecte:

1- 		-explorer switchrange	//posem el rang que vulguem

2-		-builder switchplan		//posem el pla que vulguem

3-		-miner switch			//posem l'estratègia que vulguem

4.A- 	-workflow run			//veiem com s'executa amb el rang/pla/estratègia especificat

4.B- 	-workflow run			//veiem com s'executa amb el rang/pla/estratègia especificat

4.C- 	-workflow run			//veiem com s'executa amb el rang/pla/estratègia especificat

5-		-builder switchplan		//canviem de pla

6- 		-workflow run			//veiem com s'executa amb el nou pla

7- 		-builder switchplan		//canviem de pla

8- 		-explorer switchrange	//canviem de rang a 20

9- 		-explorer start			//busquem un lloc que en cap direcció tinguem zona plana
								//(s'observarà com s'atura la seqüència i no passa res més)
				
10- 	-explorer start			//busquem un lloc on a la tercera o la quarta direcció tingui pla

11- 	-builder build			//builder passa requisits

12- 	-miner start			//miner aconsegueix els materials

13-		-builder build			//s'observarà com construeix el pla seleccionat a la zona plana trobada

14.A- 	-workflow run			//veiem com s'executa amb el rang/pla/estratègia especificat

14.B- 	-workflow run			//veiem com s'executa amb el rang/pla/estratègia especificat

14.C- 	-workflow run			//veiem com s'executa amb el rang/pla/estratègia especificat

15.		//si volem canviar rang/pla/estratègia

17- 	-explorer start			//busquem un lloc on a la tercera o la quarta direcció tingui pla

18- 	-builder build			//builder passa requisits

19- 	-miner start			//miner aconsegueix els materials

20- 	-agent pause			//el miner para		(podem fer el pause també durant el cicle de l'explorador o del builder)

20- 	-agent resume			//el miner segueix minant

20-		-builder build			//s'observarà com construeix el pla seleccionat a la zona plana trobada


