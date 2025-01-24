from z3 import *
import os
import librosa
import soundfile as sf
import numpy as np


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
opzioni_gamba_sx = []

for i in range(num_slot):
  lista_arti = [] #lista di variabili strumento
  lista_durate = [] #lista di variabili durata
  for j in range(max_arti): #itero per ogni arto
     strumento = Int(f'strumento_{i}_{j}') # creo una variabile strumento
     durata = Int(f'durata_{i}_{j}')
     lista_arti.append(strumento)
     lista_durate.append(durata)
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
  arti_per_slot.append(lista_arti)
  durate_per_slot.append(lista_durate)
 # Creo variabile opzione per battuta
  if i%(tempo*4) == 0 : # solo all'inizio della battuta
     opzione_gamba_sx = Int(f"opzione_gamba_sx_{i}")
     s.add(Or(opzione_gamba_sx == 0, opzione_gamba_sx == 1, opzione_gamba_sx == 2)) #0 non suona mai, 1 primo, 2 ultimo slot
     opzioni_gamba_sx.append(opzione_gamba_sx)


# Vincolo di Unicità degli Strumenti per Ogni Slot
for i in range(num_slot):
   for j in range(max_arti):
       for k in range(j + 1, max_arti):
          s.add(Implies(arti_per_slot[i][j] != 0,arti_per_slot[i][j] != arti_per_slot[i][k])) # se uno strumento è diverso da silenzio, gli altri devono essere diversi da questo


# vincolo sulla gamba sinistra: solo inizio, fine o mai
for i in range(num_slot):
  if i % (tempo*4) == 0: # inizio battuta
      opzione = opzioni_gamba_sx[i // (tempo*4)] # calcola l'indice giusto della variabile opzione
      s.add(Implies(opzione == 0, arti_per_slot[i][3] == 0)) #se opzione è 0 la gamba sinistra non suona mai
      s.add(Implies(opzione == 1,  arti_per_slot[i][3] != 0 )) #suona al primo slot
  elif (i+1) % (tempo*4) ==0:  # fine battuta
       opzione = opzioni_gamba_sx[i // (tempo*4)]  # calcola l'indice giusto della variabile opzione
       s.add(Implies(opzione == 2,  arti_per_slot[i][3] != 0 )) # suona all'ultimo slot

  else: #altri casi
     for opzione in opzioni_gamba_sx:
        s.add(Implies(opzione != 1, Implies(opzione!=2, arti_per_slot[i][3] == 0)))#non suona

if s.check() == sat:
  model = s.model()
  print("Soluzione trovata:\n")
  print(f"{'Slot':<6} | ", end="")
  for j in range(max_arti):
      print(f"{arti[j]:<15} | {'Dur' + str(j+1):<6} |", end="") #ora mostro il nome dell'arto
  print()
  print("-" * (6 + 24 * max_arti))

  segmenti_audio = [] #Lista per i .wav
  frequenza_campionamento = 44100 # Standard sample rate per audio
  tempo_ms = 60/100 * 1000 # calculate ms for the tempo


  for i in range(num_slot):
     print(f"{i+1:<6} |", end="")
     for j in range(max_arti):
        strumento_val = model[arti_per_slot[i][j]]
        durata_val = model[durate_per_slot[i][j]]
        print(f"{str(strumento_val):<15} | {str(durata_val):<6} |", end="")
        
        # Carica il segmento audio basato sullo strumento
        if strumento_val != 0:
            nome_strumento = ""  # Ottieni il nome file corrispondente
            match strumento_val:
                case 1:
                    nome_strumento = "0_Silenzio"
                case 1:
                    nome_strumento = "1_Cassa"
                case 2:
                    nome_strumento = "2_Rullante"
                case 3:
                    nome_strumento = "3_HiHat"
                case 4:
                    nome_strumento = "4_OpenHiHat"
                case 5:
                    nome_strumento = "5_Tom1"
                case 6:
                    nome_strumento = "6_Tom2"
                case 7:
                    nome_strumento = "7_Timpano"
                case 8:
                    nome_strumento = "8_Ride"
                case 9:
                    nome_strumento = "9_Crash"
            
            percorso_file_audio = nome_strumento + ".wav"
            if os.path.exists(percorso_file_audio):
              audio, sr = librosa.load(percorso_file_audio, sr = frequenza_campionamento)
              
              # Adjust the length of the audio segment based on 'durata_val'
              durata_segmento_samples = int((tempo_ms / durata_val) * frequenza_campionamento / 1000)
              
              # Trim or pad the audio to the correct length
              if len(audio) > durata_segmento_samples:
                  audio = audio[:durata_segmento_samples]
              elif len(audio) < durata_segmento_samples:
                  padding = np.zeros(durata_segmento_samples - len(audio))
                  audio = np.concatenate((audio, padding))
              segmenti_audio.append(audio)
            else:
               audio = np.zeros(int((tempo_ms / durata_val) * frequenza_campionamento / 1000)) #silent segment if not found
               segmenti_audio.append(audio)

        else:
              audio = np.zeros(int((tempo_ms / durata_val) * frequenza_campionamento / 1000)) #if it's silence create a silence based on the duration
              segmenti_audio.append(audio)

     print()
  print("scelte opzioni gamba sx: ", end=" ")
  for opzione in opzioni_gamba_sx:
       print(f"{model[opzione]}, ", end=" ")
  # Combine all audio segments
  audio_combinato = np.concatenate(segmenti_audio)

  # Esporta l'audio combinato come file WAV (opzionale)
  sf.write("drum_pattern.wav", audio_combinato, frequenza_campionamento)

  # # Play the combined audio (optional)
  # sf.play(audio_combinato, frequenza_campionamento)


else:
  print("Nessuna soluzione trovata")