Repozytorium zawierające kod źródłowy projektu 2 z przedmiotu ISMED - temat 5: Oprogramowanie do wizualizacji struktur RTStruct (konturów segmentacji) na obrazach CT.

Wczytywanie pliku DICOM zawierającego dane RTStruct po raz pierwszy jest czasochłonne i może powodować efekt "zawieszenia się GUI" (nie wiem jak odpalić wczytywanie w oddzielnym wątku w PyQt) - program nadal działa w tle, jednak zwyczajnie potrzebuje chwili na obsłużenie nowego pliku RTStruct. Efekt przetworzenia pliku RTStruct jest zapamiętywany w pamięci programu (taki jakby cache) i następna próba załadowania tego samego pliku z danymi RTStruct powinna przebiec dużo szybciej.

Moduł utils.py:
    Moduł zajmujący się wczytywaniem, przetwarzaniem i kombinowaniem danych obrazowych z DICOM i danych konturowych RTStruct.

    Wymagane zewnętrzne biblioteki
    -----------------------------
    matplotlib
    numpy
    pydicom
    shapely

Moduł gui.py:
    Moduł odpowiadający za graficzny interfejs użytkownika pozwalający na załadowanie pliku DICOM z danymi obrazowymi pojedynczego slice'a 
    i pliku DICOM z danymi RTStruct w celu naniesienia konturów struktur na obraz załadowanego slice'a.

    Wymagane zewnętrzne biblioteki
    -----------------------------
    PyQt5
    matplotlib
