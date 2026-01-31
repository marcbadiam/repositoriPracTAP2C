# Estructura del Projecte
Aquest fitxer proporciona una visió general de l'estructura del projecte i dels fitxers i directoris rellevants:

- **Server**: Conté el servidor.
- **docs**: Necessari per generar la documentació amb `mkdocs.yml`
- **.github**: Configuració de workflows de GitHub Actions.
- **MyAdventures**: El codi font del projecte, inclou `mcpi` que és el framework utilitzat.
- **DEMO.md**: Conté una possible seqüència d'ordres per a la demostració del projecte.
- **StartServer.bat**: Script per iniciar el servidor.
- **requirements.txt**: Conté les dependències del projecte.
- **codecov.yml**: Configuració de Codecov.

En quant al codi font del projecte, es troba a la carpeta `MyAdventures` i es troba dividit en diferents carpetes que son:

- **agents**: Implementació dels agents del sistema.
- **strategies**: Estratègies de comportament per al miner.
- **utils**: Eines i utilitats compartides, incloent el sistema de comunicació.
- **tests**: Conjunt de tests unitaris.
- **mcpi**: Llibreria d'interfície amb Minecraft.
- **data**: Fitxers csv per generar planols.

També hi trobem fitxers solts (dins MyAdventures) com:
- **run_log_analysis.bat**: Script per executar l'anàlisi de logs (crida a `analyze_logs.py`).
- **test_quick.py**: Script per executar tests ràpids durant el desenvolupament.
- **run_tests.bat**: Script per executar els tests unitaris.
- **run.py**: El punt d'entrada principal per executar el sistema.
