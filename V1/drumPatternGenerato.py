import tkinter as tk
from tkinter import ttk
from z3 import *

def genera_pattern():
    # Raccolta degli input dall'interfaccia
    num_slot = int(num_slot_combobox.get())  # Prendi il numero di slot
    stile_musicale = stile_combobox.get()  # Prendi lo stile musicale
    print("Numero di Slot:", num_slot)
    print("Stile Musicale:", stile_musicale)

    # Parametri Pattern
    max_strumenti = 4
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
    strumenti_per_slot = [] #matrice di variabili strumento
    durate_per_slot = [] # matrice di variabili durata

    for i in range(num_slot):
        strumenti_list = [] #lista per ogni slot
        durate_list = [] #lista per ogni slot
        for j in range(max_strumenti): #itero fino a max_strumenti
           strumento = Int(f'strumento_{i}_{j}') # creo una variabile strumento
           durata = Int(f'durata_{i}_{j}')
           strumenti_list.append(strumento) #aggiungo la variabile strumento alla lista per quello slot
           durate_list.append(durata)
           s.add(Or([strumento == st for st in strumenti])) # vincolo sul range degli strumenti
           s.add(Or([durata == d for d in durate]))
        strumenti_per_slot.append(strumenti_list) #aggiungo la lista alla matrice principale
        durate_per_slot.append(durate_list)

    # Aggiungo un vincolo: il primo strumento di ogni slot non è silenzio
    for i in range(num_slot):
        s.add(strumenti_per_slot[i][0] != 0)


    # Vincolo Hi-Hat e altri strumenti in base allo stile
    if stile_musicale == "Rock":
      for i in range(num_slot):
        if i % 2 == 0:  # Impone HiHat solo negli slot dispari
            s.add(strumenti_per_slot[i][0] == 3)  # HiHat nel primo strumento
            s.add(strumenti_per_slot[i][1] == 1)  # cassa nel secondo strumento
        else:
            s.add(strumenti_per_slot[i][2] == 2) #Rullante nello strumento 2
        
        #aggiungo vincolo solo se il primo strumento è la cassa (1)
        at_least_one_other = False
        for j in range(1, max_strumenti):
            s.add(Implies(strumenti_per_slot[i][j] != 0, True))
            at_least_one_other = Or(at_least_one_other, strumenti_per_slot[i][j]!=0)
        s.add(at_least_one_other)

    else: # Jazz, Blues o Default: Hi-Hat nel primo strumento di ogni slot e almeno un altro strumento che non è silenzio
       for i in range(num_slot):
          s.add(strumenti_per_slot[i][0] == 3) # hihat nel primo strumento di ogni slot
          at_least_one_other = False
          for j in range(1, max_strumenti):
              s.add(Implies(strumenti_per_slot[i][j] != 0, True))
              at_least_one_other = Or(at_least_one_other, strumenti_per_slot[i][j]!=0)
          s.add(at_least_one_other)


    if s.check() == sat:
        model = s.model()
        print("Soluzione trovata:\n")
        print(f"{'Slot':<6} | ", end="")
        for j in range(max_strumenti):
             print(f"{'Str' + str(j+1):<10} | {'Dur' + str(j+1):<6} |", end="")
        print()
        print("-" * (6 + (10 + 8) * max_strumenti))

        for i in range(num_slot):
          print(f"{i+1:<6} |", end="")
          for j in range(max_strumenti):
              strumento_val = model[strumenti_per_slot[i][j]]
              durata_val = model[durate_per_slot[i][j]]
              print(f"{str(strumento_val):<10} | {str(durata_val):<6} |", end="")
          print()

    else:
        output_text.insert(tk.END, "Nessuna soluzione trovata\n")

# Creazione della finestra
window = tk.Tk()
window.title("Generatore di Pattern Ritmici")

# Elementi
num_slot_label = ttk.Label(window, text="Numero di Slot:")
num_slot_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
num_slot_combobox = ttk.Combobox(window, values=[2, 4, 8, 16], width=5)
num_slot_combobox.set(16)
num_slot_combobox.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)

stile_label = ttk.Label(window, text="Stile Musicale:")
stile_label.grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
stile_combobox = ttk.Combobox(window, values=["Rock", "Jazz", "Blues", "Default"], width=10)
stile_combobox.set("Default")
stile_combobox.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)

genera_button = ttk.Button(window, text="Genera", command=genera_pattern)
genera_button.grid(row=2, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)

output_text = tk.Text(window)
output_text.grid(row=3, column=0, columnspan=2, padx=5, pady=5)

# Avvia la finestra
window.mainloop()