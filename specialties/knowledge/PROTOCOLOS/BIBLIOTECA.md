# 📚 Protocolo: Biblioteca — Préstamo de Libros

> Prioridad: 🟡 MEDIA
> Última revisión: 2026-07-03

## Propósito
Gestionar el préstamo de libros digitales desde la Biblioteca de Trantor.
Cuando Luisa pida un libro → buscarlo, copiarlo a "libros en uso", confirmar.

---

## 📊 Catálogo General

**Total:** ~75,454 EPUBs clasificados | ~89 GB (con manga, partituras, etc.)

### Géneros disponibles (top 20)

| Género | Cantidad |
|---|---|
| Novela | 21,289 |
| Romántico | 14,155 |
| Intriga | 7,314 |
| Policial | 7,160 |
| Aventuras | 6,296 |
| Ciencia ficción | 5,996 |
| Histórico | 5,319 |
| Fantástico | 4,931 |
| Drama | 4,552 |
| Historia | 3,316 |
| Otros | 3,206 |
| Juvenil | 2,871 |
| Realista | 2,736 |
| Terror | 2,432 |
| Relato | 2,273 |
| Erótico | 2,224 |
| Ciencias sociales | 2,210 |
| Divulgación | 2,082 |
| Humor | 1,936 |
| Memorias | 1,894 |

### También hay (100-1000+ cada uno)
Filosofía, Infantil, Espiritualidad, Autoayuda, Psicológico, Ciencias naturales, Ensayo, Sátira, Poesía, Teatro, Cocina, Viajes, Arte, Sexualidad, Salud, Tecnología, Idiomas, Manuales

---

## 📖 Libros destacados por género

### Novela (21,289)
Autores principales: A. C. Baantjer, A. B. Yehoshua, A. Belén Hernández, + miles más...
Series notables: Kay Scarpetta, Comisario Maigret, Perry Mason, Adam Dalgliesh

### Ciencia Ficción (5,996)
- A. A. Attanasio — Radix
- A. A. Espigares-Sánchez — Lanzado al vacío
- A. E. Van Vogt — (varios)
- Star Wars series, Star Trek series
- Warhammer 40000 — Herejía de Horus
- BattleTech series
- Antologías de Ciencia Ficción Caralt
- Nova series

### Fantástico (4,931)
- A. A. Attanasio — El dragón y el unicornio, El lobo y la corona, Reino del Grial
- A. B. Blanco — El manuscrito oculto de los celtas
- Mundos de tinieblas — Novelas de tribu
- Saga Los MacGregor
- Ángeles Caídos

### Romántico (14,155)
- A. C. Arthur — Creciente tentación, Seducción letal
- A. C. Balton — El paraíso olvidado, Los secretos del Gran Rey
- A. Belén Hernández — La protección cabani, La vida es así…
- Bianca series
- Aurors Roe Teagarden series

### Aventuras (6,296)
- A. B. Guthrie Jr. — Bajo cielos inmensos
- Richard Sharpe series
- Tarzán series
- Aubrey y Maturin series
- Amelia Peabody series

### Terror (2,432)
- El pequeño vampiro series
- Amantes perversos (oscuros y peligrosos)

### Policial / Intriga (7,160 / 7,314)
- A. C. Baantjer — Muerte en Ámsterdam
- A. B. Vázquez — Carolina
- Perry Mason series
- Adam Dalgliesh series
- Kay Scarpetta series
- Comisario Maigret series
- Belascoarán Shayne
- Alex Delaware series
- Agatha Mistery series

### Histórico (5,319)
- A. A. Attanasio — El dragón y el unicornio (histórico + fantástico)
- Biblioteca Sven Hassel
- Enciclopedia de México

### Humor (1,936)
- @diostuitero — La Biblia según Dios
- @norcoreano — El libro rojo de Norcoreano
- @SrtaBebi — Amor y asco, Indomable

---

## ⚙️ Proceso de préstamo

1. Luisa pide un libro (título o autor)
2. Buscar en Trantor:
   ```bash
   ssh trantor "findstr /i \"título\" E:\Biblioteca\biblioteca_clasificada.txt"
   # o buscar por archivo:
   ssh trantor "dir E:\Biblioteca\Biblioteca /B /S 2>nul | findstr /i \"título\""
   ```
3. Copiar a "libros en uso":
   ```bash
   ssh trantor "copy \"E:\Biblioteca\Biblioteca\autor\título.epub\" \"E:\Biblioteca\libros en uso\\\""
   ```
4. Transferir a Coruscant (opcional):
   ```bash
   scp trantor:"E:\\Biblioteca\\libros en uso\\título.epub" ~/Trantor/libros_en_uso/
   ```
5. Confirmar a Luisa que está disponible

## Ubicaciones
- **Catálogo clasificado:** `E:\Biblioteca\biblioteca_clasificada.txt` (75,454 EPUBs)
- **Catálogo físico:** `E:\Biblioteca\Biblioteca\` (por autor/nombre)
- **Libros en uso:** `E:\Biblioteca\libros en uso\`
- **Gestor ebook:** `E:\Biblioteca\Calibre\` (metadatos en metadata.db)
- **Otros formatos:** `E:\Biblioteca\Berserk Full\` (CBR/CBZ manga), `E:\Biblioteca\Partituras violin\`

## Notas
- ~89 GB en toda la Biblioteca. No se migra completa sin consultar.
- Formato principal: EPUB
- Proceso es préstamo bajo demanda, no migración masiva.
- `biblioteca_clasificada.txt` ya tiene reseñas cortas de cada libro.
