# Oprogramowanie do wizualizacji struktur RTStruct (konturów segmentacji) na obrazach CT.


## Moduł utils.py:  
Moduł zajmujący się wczytywaniem, przetwarzaniem, kombinowaniem i rysowaniem danych obrazowych z DICOM i danych konturowych RTStruct.

### Wymagane zewnętrzne biblioteki:
- matplotlib
- numpy
- pydicom
- shapely

## Moduł gui.py:
Moduł odpowiadający za graficzny interfejs użytkownika pozwalający na załadowanie pliku DICOM z danymi obrazowymi pojedynczego slice'a 
i pliku DICOM z danymi RTStruct w celu naniesienia konturów struktur na obraz załadowanego slice'a. Interfejs użytkownika wyposażony jest w toolbar **matplotlib** co umożliwia
nawigację po wyświetlanym obrazie, przybliżanie, oddalanie, zapis wyświetlanego obrazu m.in. do formatu jpeg, png, svd.  
Moduł **gui.py** wykorzystuje klasy i funkcje zdefiniowane w module **utils.py**.

### Wymagane zewnętrzne biblioteki
- PyQt5
- matplotlib

## Prezentacja działania programu
![image](https://user-images.githubusercontent.com/62251572/156835881-5ac0671a-d0c1-45aa-a492-4a2bb58e1142.png)
![image](https://user-images.githubusercontent.com/62251572/156836120-d76f0e3e-4625-44ec-a1cc-3bcb3057fa46.png)
![image](https://user-images.githubusercontent.com/62251572/156836252-45d01cce-16c5-44d5-b65d-40365700faae.png)
![image](https://user-images.githubusercontent.com/62251572/156836373-158c42bb-875e-4593-b2ba-b1223f83b021.png)
![image](https://user-images.githubusercontent.com/62251572/156836457-5ff79bd9-3cf5-4d44-ab48-7369cdef2760.png)
![image](https://user-images.githubusercontent.com/62251572/156836768-0dff2d51-6b99-4909-94f5-fb52330e2412.png)
![image](https://user-images.githubusercontent.com/62251572/156835313-79f738b9-bc4e-4d98-a8ba-443a4d407713.png)
![image](https://user-images.githubusercontent.com/62251572/156835677-8d00ecf5-ebe3-494e-8527-65a556599f73.png)
