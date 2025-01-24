import os
os.environ['LIBROSA_AUDIO'] = 'soundfile' #imposta la variabile d'ambiente.

from z3 import *
import soundfile as sf
import numpy as np
import librosa


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
conteggi_tre_arti = []
conteggi_cassa = {}  # nuovo dizionario per contare le casse consecutive

for i in range(num_slot):
    lista_arti = [] #lista di variabili strumento
    durate_list = [] #lista di variabili durata #Ora qui è definita
    for j in range(max_arti): #itero per ogni arto
       strumento = Int(f'strumento_{i}_{j}') # creo una variabile strumento
       durata = Int(f'durata_{i}_{j}')
       lista_arti.append(strumento)
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
    arti_per_slot.append(lista_arti)
    durate_per_slot.append(durate_list)
    # Creo variabile opzione per battuta
    if i % (tempo*4) == 0: # solo all'inizio della battuta
       opzione_gamba_sx = Int(f"opzione_gamba_sx_{i}")
       s.add(Or(opzione_gamba_sx == 0, opzione_gamba_sx == 1, opzione_gamba_sx == 2)) #0 non suona mai, 1 primo, 2 ultimo slot
       opzioni_gamba_sx.append(opzione_gamba_sx)
       conteggio = Int(f"conteggio_{i}") #creo una variabile conteggio per la battuta
       conteggi_tre_arti.append(conteggio) #metto la variabile conteggio nella lista
       s.add(conteggio == 0 ) # imposto a zero all'inizio della battuta.
    # Inizializzazione del contatore di casse per ogni battuta
    if i % (tempo*4) == 0:
        conteggi_cassa[i] = Int(f"conteggio_cassa_{i}")
        s.add(conteggi_cassa[i] == 0)


# Vincolo di Unicità degli Strumenti per Ogni Slot
for i in range(num_slot):
     for j in range(max_arti):
         for k in range(j + 1, max_arti):
            s.add(Implies(And(arti_per_slot[i][j] != 0,arti_per_slot[i][k] != 0),Or(arti_per_slot[i][j] != arti_per_slot[i][k] ,  Or(arti_per_slot[i][j]==4,arti_per_slot[i][k]==4)))) # se uno strumento è diverso da silenzio, gli altri devono essere diversi da questo, a meno che non siano entrambi open hi hat

#vincolo open hihat
for i in range (num_slot): #per ogni slot
   s.add(Implies(arti_per_slot[i][3] !=0, arti_per_slot[i][0] == 4)) #se gamba sx suona open hi hat allora mano dx open hi hat.
          
if s.check() == sat:
    model = s.model()
    print("Soluzione trovata:\n")
    print(f"{'Slot':<6} | ", end="")
    for j in range(max_arti):
        print(f"{arti[j]:<15} | {'Dur' + str(j+1):<6} |", end="") #ora mostro il nome dell'arto
    print()
    print("-" * (6 + 24 * max_arti))

    segmenti_audio = []  # Lista per i .wav
    frequenza_campionamento = 44100  # Standard sample rate per audio
    tempo_ms = 300 / 100 * 1000  # calcola ms per il tempo


    for i in range(num_slot):
       print(f"{i+1:<6} |", end="")
       strumenti_segmento = []
       durata_segmento_samples = 0
       for j in range(max_arti):
          strumento_val = int(model[arti_per_slot[i][j]].as_long())  # accedo al valore concreto dal modello e lo converto in intero python.
          durata_val = int(model[durate_per_slot[i][j]].as_long())  # accedo al valore concreto dal modello e lo converto in intero python.
          print(f"{str(strumento_val):<15} | {str(durata_val):<6} |", end="")
          # Carica il segmento audio basato sullo strumento
          if strumento_val != 0:
              nome_strumento = ""  # Ottieni il nome file corrispondente
              match strumento_val:
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

              percorso_file_audio = "Strumenti/" + nome_strumento + ".wav"  # aggiungo la cartella Strumenti/ all'inizio.
              if os.path.exists(percorso_file_audio):
                try:
                    audio_segmento, sr = librosa.load(percorso_file_audio, sr=frequenza_campionamento, mono=True)  # carico con librosa e forzo mono
                    audio_segmento = audio_segmento.astype(np.float32) # Convert to float32
                    strumenti_segmento.append(audio_segmento) #carico con librosa.
                except Exception as e:
                   print(f"ATTENZIONE: Errore nel caricamento con soundfile del file {percorso_file_audio}: {e}")
                   strumenti_segmento.append(np.zeros((int((tempo_ms / durata_val) * frequenza_campionamento / 1000),1),dtype=np.float32)) # creo l'array di zeri 2D.
                
              else:
                   print(f"ATTENZIONE: File audio {percorso_file_audio} non trovato, verrà aggiunto un segmento di silenzio")
                   strumenti_segmento.append(np.zeros((int((tempo_ms / durata_val) * frequenza_campionamento / 1000),1),dtype=np.float32))  # silent segment if not found
          else:
             durata_segmento_samples = int((tempo_ms / durata_val) * frequenza_campionamento / 1000)  # if it's silence create a silence based on the duration
             strumenti_segmento.append(np.zeros((durata_segmento_samples,1),dtype=np.float32))  # if it's silence create a silence based on the duration
       
       durata_segmento_samples = int((tempo_ms / durata_val) * frequenza_campionamento / 1000)
       audio_combinato = np.zeros((durata_segmento_samples, 1), dtype=np.float32) #creo una matrice di zeri della lunghezza corretta.

       for audio_segmento in strumenti_segmento:
           audio_combinato = audio_combinato + audio_segmento[:durata_segmento_samples] #sommo gli strumenti

       segmenti_audio.append(audio_combinato)

       print()
    print("scelte opzioni gamba sx: ", end=" ")
    for opzione in opzioni_gamba_sx:
        print(f"{model[opzione]}, ", end=" ")
    # Combine all audio segments
    print(f"lunghezza segmenti_audio = {len(segmenti_audio)}")
    audio_combinato = np.concatenate(segmenti_audio, axis=0)  # concateno rispetto all'asse 0 (righe).

    # Esporta l'audio combinato come file WAV (opzionale)
    sf.write("drum_pattern.wav", audio_combinato, frequenza_campionamento)

    # # Play the combined audio (optional)
    # sf.play(audio_combinato, frequenza_campionamento)


else:
    print("Nessuna soluzione trovata")