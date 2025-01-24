import z3
import soundfile as sf
import librosa
import numpy as np
import os
import audioread

# Configura audioread per usare soundfile:
audioread.plugins.add(".mp3", sf.read)
audioread.plugins.add(".wav", sf.read)

# --- Configurazione ---
NUM_SLOT = 16
NUM_ARTI = 4  # Mano destra, mano sinistra, gamba destra, gamba sinistra
TEMPO_BATTUTA = 4  # 4/4
DURATA_NOTE = [1/16, 1/8, 1/4]  # Sedicesimi, ottavi, quarti
STRUMENTI = {
    "silenzio": "0_Silenzio.mp3",
    "cassa": "1_Cassa.mp3",
    "rullante": "2_Rullante.mp3",
    "hihat": "3_HiHat.mp3",
    "open_hihat": "4_OpenHiHat.mp3",
    "tom1": "5_Tom1.mp3",
    "tom2": "6_Tom2.mp3",
    "timpano": "7_Timpano.mp3",
    "ride": "8_Ride.mp3",
    "crash": "9_Crash.mp3",
    "cowbell": "10_Cowbell.mp3",
}
CARTELLE_STRUMENTI = "Strumenti"

def carica_suoni():
    suoni = {}
    for strumento, filename in STRUMENTI.items():
      try:
          suono, sr = librosa.load(os.path.join(CARTELLE_STRUMENTI, filename), sr=None)
          suoni[strumento] = suono, sr
      except Exception as e:
          print(f"Errore nel caricamento del suono {filename}: {e}")
          return None  # Errore critico

    return suoni

# Funzione per applicare la durata ad un suono
def durata_suono(suono, sr, durata, durata_originale = None):
  if durata_originale is None:
    durata_originale = len(suono)/sr
  nuova_lunghezza = int(durata * sr)
  if nuova_lunghezza > len(suono): # se la durata è maggiore allungo il suono originale
    suono_esteso = np.tile(suono, int(np.ceil(nuova_lunghezza / len(suono))))[:nuova_lunghezza]
    return suono_esteso
  else:
     return suono[:nuova_lunghezza]

# Funzione per creare un pattern basato su Z3
def crea_pattern(suoni):
    s = z3.Solver()

    # Variabili per la selezione degli strumenti
    strumenti_variabili = {}
    for slot in range(NUM_SLOT):
        for arto in range(NUM_ARTI):
            strumenti_variabili[(slot, arto)] = z3.Int(f"strumento_{slot}_{arto}")

    # Vincoli
    # Ogni arto suona solo uno strumento alla volta (0 = niente, 1 = cassa, 2 = rullante, 3 = hi-hat, 4 = open_hihat)
    for slot in range(NUM_SLOT):
        for arto in range(NUM_ARTI):
           s.add(z3.And(strumenti_variabili[(slot, arto)] >= 0, strumenti_variabili[(slot, arto)] <= 4))


    # Gamba sinistra (arto 3) può suonare solo all'inizio, fine di battuta o mai
    for slot in range(NUM_SLOT):
        if slot % (NUM_SLOT/TEMPO_BATTUTA) != 0 and slot % (NUM_SLOT/TEMPO_BATTUTA) != (NUM_SLOT/TEMPO_BATTUTA - 1):
           s.add(strumenti_variabili[(slot, 3)] == 0)

    # open hi-hat da mano destra(0) e gamba sinistra(3)
    for slot in range(NUM_SLOT):
        s.add(z3.Implies(strumenti_variabili[(slot, 0)] == 4, strumenti_variabili[(slot, 3)] == 4))
        s.add(z3.Implies(strumenti_variabili[(slot, 3)] == 4, strumenti_variabili[(slot, 0)] == 4))

    # Soluzione
    if s.check() == z3.sat:
        model = s.model()
        pattern = {}
        for slot in range(NUM_SLOT):
            pattern[slot] = {}
            for arto in range(NUM_ARTI):
                strumento_index = model.eval(strumenti_variabili[(slot, arto)]).as_long()
                strumento = list(STRUMENTI.keys())[strumento_index] if strumento_index > 0 else None
                pattern[slot][arto] = strumento

        return pattern
    else:
        print("Nessun pattern trovato che soddisfi i vincoli.")
        return None

# Funzione per combinare i suoni di uno slot
def combia_suoni_slot(pattern_slot, suoni, sr_principale):
   suoni_slot = []
   for arto in pattern_slot.keys():
        strumento = pattern_slot[arto]
        if strumento and strumento != "cowbell":
           suono_strumento, sr_strumento = suoni[strumento]
           if sr_strumento != sr_principale:
               suono_strumento = librosa.resample(suono_strumento, orig_sr=sr_strumento, target_sr=sr_principale)

           durata = DURATA_NOTE[0] # Durata minima (sedicesimo)
           suoni_slot.append(durata_suono(suono_strumento, sr_principale, durata))
   
   # combinazione di tutti i suoni dello slot
   if len(suoni_slot) > 0:
       max_len = max(len(suono) for suono in suoni_slot)
       suono_combinato = np.zeros(max_len)
       for suono in suoni_slot:
           suono_combinato[:len(suono)] += suono
       return suono_combinato
   else: return None


# Funzione per generare l'audio
def genera_audio(pattern, suoni):
    audio_totale = np.array([])
    sr_principale = list(suoni.values())[0][1] # Prende la frequenza di campionamento del primo suono

    for slot in range(NUM_SLOT):
      suono_slot = combia_suoni_slot(pattern[slot], suoni, sr_principale)
      if suono_slot is not None:
        audio_totale = np.concatenate((audio_totale,suono_slot ))

      if (slot+1) % (NUM_SLOT/TEMPO_BATTUTA) == 0: # aggiungo il cowbell alla fine della battuta
          cowbell, sr_cowbell = suoni["cowbell"]
          if sr_cowbell != sr_principale:
               cowbell = librosa.resample(cowbell, orig_sr=sr_cowbell, target_sr=sr_principale)
          durata_cowbell = DURATA_NOTE[0] #durata di un sedicesimo
          cowbell_con_durata = durata_suono(cowbell, sr_principale, durata_cowbell)
          audio_totale = np.concatenate((audio_totale, cowbell_con_durata))

    return audio_totale, sr_principale

# Funzione principale
def main():
    suoni = carica_suoni()
    if suoni is None:
        print("Errore nel caricamento dei suoni.")
        return

    pattern = crea_pattern(suoni)
    if pattern:
        audio, sr = genera_audio(pattern, suoni)
        sf.write("batteria_generata.wav", audio, sr)
        print("File audio generato: batteria_generata.wav")

if __name__ == "__main__":
    main()

