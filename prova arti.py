from z3 import *

# Parametri Pattern
num_slot = 16  # numero di slot totali
max_arti = 4  # numero di arti (mano dx, mano sx, gamba dx, gamba sx)
tempo = 4 # tempi per battuta

# Durate: 1 = sedicesimo, 2 = ottavo, 4 = quarto
durate = [1, 2, 4]

# Strumenti: 0 = silenzio, 1 = Cassa, 2 = Rullante, 3 = Hi-hat/Charleston, 4 = OPEN-hihat, 5 = Tom1, 6 = Tom2, 7 = Timpano, 8 = Ride, 9 = Crash
strumenti = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

#
strumenti_arti = {
    0: [], #silenzio
    1: ["gamba_destra"],  # cassa
    2: ["mano_sinistra", "mano_destra"],  # rullante
    3: ["mano_destra"],  # hihat
    4: ["mano_destra", "gamba_sinistra"],  # OpenHiHat (potrebbe essere suonato con entrambe le mani)
    5: ["mano_destra", "mano_sinistra"], # tom1
    6: ["mano_destra", "mano_sinistra"], #tom2
    7: ["mano_destra", "mano_sinistra"], #timpano
    8: ["mano_destra"], #ride
    9: ["mano_destra"] #crash
}

arti = ["mano_destra", "mano_sinistra", "gamba_destra", "gamba_sinistra"]

s = Solver()  # crea un solver di Z3

# Liste per memorizzare le variabili create
arti_per_slot = []  # matrice delle variabili per gli arti
durate_per_slot = [] # matrice per le durate degli arti

# creo una variabile booleana per l'opzione della gamba sinistra
gamba_sx_opzioni = []

for i in range(num_slot):
    arti_list = [] #lista di variabili strumento
    durate_list = [] #lista di variabili durata
    for j in range(max_arti): #itero per ogni arto
       strumento = Int(f'strumento_{i}_{j}') # creo una variabile strumento
       durata = Int(f'durata_{i}_{j}')
       arti_list.append(strumento)
       durate_list.append(durata)
       s.add(Or([strumento == st for st in strumenti]))  # vincoli sul range degli strumenti
       s.add(Or([durata == d for d in durate]))  # vincoli sul range delle durate
       # Crea un vincolo per assicurarmi che l'arto sia suonato con uno strumento disponibile
       if j==0:
          s.add(Or([strumento == st for st in strumenti if "mano_destra" in strumenti_arti[st]  ]))
       elif j==1:
          s.add(Or([strumento == st for st in strumenti if "mano_sinistra" in strumenti_arti[st]]))
       elif j==2:
          s.add(Or([strumento == st for st in strumenti if "gamba_destra" in strumenti_arti[st]]))
       elif j==3:
          s.add(Or([strumento == st for st in strumenti if "gamba_sinistra" in strumenti_arti[st]]))
    arti_per_slot.append(arti_list)
    durate_per_slot.append(durate_list)
   # Creo variabile opzione per battuta
    if i%(tempo*4) == 0 : # solo all'inizio della battuta
       gamba_sx_opzione = Int(f"gamba_sx_opzione_{i}")
       s.add(Or(gamba_sx_opzione == 0, gamba_sx_opzione == 1, gamba_sx_opzione == 2)) #0 non suona mai, 1 primo, 2 ultimo slot
       gamba_sx_opzioni.append(gamba_sx_opzione)


# Vincolo di Unicità degli Strumenti per Ogni Slot
for i in range(num_slot):
     for j in range(max_arti):
         for k in range(j + 1, max_arti):
            s.add(Implies(arti_per_slot[i][j] != 0,arti_per_slot[i][j] != arti_per_slot[i][k])) # se uno strumento è diverso da silenzio, gli altri devono essere diversi da questo


# vincolo sulla gamba sinistra: solo inizio, fine o mai
for i in range(num_slot):
    if i % (tempo*4) == 0: # inizio battuta
        opzione = gamba_sx_opzioni[i // (tempo*4)] # calcola l'indice giusto della variabile opzione
        s.add(Implies(opzione == 0, arti_per_slot[i][3] == 0)) #se opzione è 0 la gamba sinistra non suona mai
        s.add(Implies(opzione == 1,  arti_per_slot[i][3] != 0 )) #suona al primo slot
    elif (i+1) % (tempo*4) ==0:  # fine battuta
         opzione = gamba_sx_opzioni[i // (tempo*4)]  # calcola l'indice giusto della variabile opzione
         s.add(Implies(opzione == 2,  arti_per_slot[i][3] != 0 )) # suona all'ultimo slot

    else: #altri casi
       for opzione in gamba_sx_opzioni:
          s.add(Implies(opzione != 1, Implies(opzione!=2, arti_per_slot[i][3] == 0)))#non suona



if s.check() == sat:
    model = s.model()
    print("Soluzione trovata:\n")
    print(f"{'Slot':<6} | ", end="")
    for j in range(max_arti):
        print(f"{arti[j]:<15} | {'Dur' + str(j+1):<6} |", end="") #ora mostro il nome dell'arto
    print()
    print("-" * (6 + 24 * max_arti))

    for i in range(num_slot):
       print(f"{i+1:<6} |", end="")
       for j in range(max_arti):
          strumento_val = model[arti_per_slot[i][j]]
          durata_val = model[durate_per_slot[i][j]]
          print(f"{str(strumento_val):<15} | {str(durata_val):<6} |", end="")
       print()
    print("scelte opzioni gamba sx: ", end=" ")
    for opzione in gamba_sx_opzioni:
         print(f"{model[opzione]}, ", end=" ")


else:
    print("Nessuna soluzione trovata")