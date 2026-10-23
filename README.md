# Čelix 🇷🇸🐧

**Čelix** je open-source alternativa zvaničnoj aplikaciji *Čelik* (MUP Republike Srbije), namenjena za očitavanje elektronskih ličnih karata na Linux operativnim sistemima.

Cilj projekta je da obezbedi stabilno, jednostavno i potpuno izvorno (native) rešenje za Linux korisnike, bez potrebe za emulatorima poput Wine-a ili virtuelnim mašinama.

---

## Mogućnosti

- Očitavanje osnovnih podataka sa čipa lične karte (ime, prezime, JMBG, adresa, itd.)
- Prikaz i čuvanje biometrijske fotografije
- Prikaz statusa i detalja sertifikata
- Izvoz očitanih podataka u PDF ili JSON format
- Podrška za standardne PC/SC pametne čitače kartica

---

## Instalacija i pokretanje

Pokretanje aplikacije:

```bash
#  ./celik_linux
```

---

## Desktop integracija

Ukoliko želite da dodate prečicu u meni vašeg grafičkog okruženja, možete iskoristiti priloženi `.desktop` fajl:

```bash
cp celix.desktop ~/.local/share/applications/
```

---

## Odricanje odgovornosti (Disclaimer)

Ovaj projekat je nezavisan, open-source projekat i **nije** zvanična aplikacija Ministarstva unutrašnjih poslova Republike Srbije. Svi nazivi i žigovi pripadaju njihovim vlasnicima. Aplikacija pristupa samo javno dostupnim podacima sa čipa koji ne zahtevaju administratorske PIN kodove.

---

## Licenca

Ovaj projekat je licenciran pod [GPL-2.0] licencom.
