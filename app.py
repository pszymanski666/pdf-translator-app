import streamlit as st
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
import os
import json
from openai import OpenAI

# --- Konfiguracja ---

# WAŻNE: Wstaw tutaj swój klucz API OpenRouter.
# Pamiętaj, aby nie umieszczać prawdziwego klucza w publicznych repozytoriach!
# Możesz też wczytywać go ze zmiennej środowiskowej dla większego bezpieczeństwa.
OPENROUTER_API_KEY = st.secrets["Openrouter_key"]  # <--- ZASTĄP SWOIM KLUCZEM

# Wczytaj komunikaty systemowe z pliku JSON
try:
    with open("system_messages.json", "r", encoding="utf-8") as f:
        SYSTEM_MESSAGES = json.load(f)
except FileNotFoundError:
    st.error("Nie znaleziono pliku system_messages.json!")
    SYSTEM_MESSAGES = {"default": "Error: system_messages.json not found."}
except json.JSONDecodeError:
    st.error("Błąd podczas parsowania pliku system_messages.json!")
    SYSTEM_MESSAGES = {"default": "Error: Could not parse system_messages.json."}

# Opcjonalna wiadomość systemowa dla modelu LLM. Można ją dostosować.
# SYSTEM_MESSAGE = """... (usunięto długi ciąg znaków) ...""" # Usunięto statyczną definicję

# Dostępne języki (Wyświetlana nazwa: kod Tesseract / kod dla LLM)
LANGUAGES = {
    "Angielski": ("eng", "English"),
    "Niemiecki": ("deu", "German"),
    "Polski": ("pol", "Polish"),
    "Gruziński": ("kat", "Georgian"),
    "Ukraiński": ("ukr", "Ukrainian"),
    "Chiński (Uproszczony)": ("chi-sim", "Simplified Chinese"),
    "Chiński (Tradycyjny)": ("chi-tra", "Traditional Chinese"),
    "Francuski": ("fra", "French"),
    "Hiszpański": ("spa", "Spanish"),
    "Hinduski": ("hin", "Hindi"),
    "Turecki": ("tur", "Turkish"),
}

# --- Funkcje pomocnicze ---

def extract_images_from_pdf(pdf_bytes):
    """Ekstrahuje obrazy stron z pliku PDF."""
    images = []
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            # Renderuj stronę jako obraz PNG w wysokiej rozdzielczości (300 DPI)
            pix = page.get_pixmap(dpi=300)
            img_bytes = pix.tobytes("png")
            images.append(Image.open(io.BytesIO(img_bytes)))
        doc.close()
        return images
    except Exception as e:
        st.error(f"Błąd podczas przetwarzania PDF: {e}")
        return None

def perform_ocr(images, lang_code):
    """Wykonuje OCR na liście obrazów używając Tesseract."""
    full_text = ""
    try:
        # Sprawdzenie, czy Tesseract jest zainstalowany i dostępny
        try:
            pytesseract.get_tesseract_version()
        except pytesseract.TesseractNotFoundError:
            st.error("Tesseract nie jest zainstalowany lub nie ma go w ścieżce systemowej (PATH).")
            st.error("Instrukcje instalacji: https://tesseract-ocr.github.io/tessdoc/Installation.html")
            return None

        for i, img in enumerate(images):
            st.write(f"Przetwarzanie strony {i+1}/{len(images)}...")
            # Konwersja obrazu PIL do formatu akceptowanego przez Tesseract
            text = pytesseract.image_to_string(img, lang=lang_code)
            full_text += text + "\n\n"  # Dodaj separator między stronami
        return full_text.strip()
    except Exception as e:
        st.error(f"Błąd podczas OCR: {e}")
        return None

def translate_text_stream(text_to_translate, source_lang_name, target_lang_llm):
    """Wysyła tekst do OpenRouter API i streamuje tłumaczenie."""
    if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == "sk-or-v1-...":
        st.error("Klucz API OpenRouter nie został ustawiony. Edytuj plik app.py.")
        return None

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )

    prompt = f"Przetłumacz poniższy tekst z {source_lang_name} na {target_lang_llm}:\n\n{text_to_translate}"

    # Pobierz odpowiedni komunikat systemowy
    system_message_content = SYSTEM_MESSAGES.get(target_lang_llm, SYSTEM_MESSAGES.get("default"))
    if not system_message_content:
        st.warning("Nie znaleziono domyślnego komunikatu systemowego. Używam pustego.")
        system_message_content = ""

    try:
        print(system_message_content)
        print(prompt)
        stream = client.chat.completions.create(
            model="google/gemma-3-27b-it",
            messages=[
                {"role": "system", "content": system_message_content},
                {"role": "user", "content": prompt},
            ],
            stream=True,
            temperature=0.1,
            top_p=0.95,
        )
        return stream
    except Exception as e:
        st.error(f"Błąd podczas komunikacji z OpenRouter API: {e}")
        return None

# --- Interfejs Użytkownika Streamlit ---

st.set_page_config(layout="wide") # Użyj szerokiego layoutu

# Dodaj niestandardowy CSS, aby zmniejszyć górny padding
st.markdown("""
<style>
    /* Celuje w główny kontener bloku */
    .block-container {
        padding-top: 1rem !important; /* Możesz dostosować tę wartość (np. 0rem) */
    }
    /* Czasami potrzeba bardziej specyficznego selektora */
    /* div[data-testid="stAppViewBlockContainer"] {
        padding-top: 1rem !important;
    }*/
</style>
""", unsafe_allow_html=True)

st.title("📄 PDF Translator Demo (OCR + LLM)")

# --- Pasek Boczny (Sidebar) ---
with st.sidebar:
    st.header("Ustawienia Tłumaczenia")

    uploaded_file = st.file_uploader(
        "1. Załaduj plik PDF (bez warstwy tekstowej)", type="pdf"
    )

    ocr_lang_name = st.selectbox(
        "2. Wybierz język źródłowy (OCR):",
        options=list(LANGUAGES.keys()),
        index=0,  # Domyślnie Angielski
    )
    ocr_lang_code = LANGUAGES[ocr_lang_name][0]

    target_lang_name = st.selectbox(
        "3. Wybierz język docelowy (Tłumaczenie):",
        options=list(LANGUAGES.keys()),
        index=2,  # Domyślnie Polski
    )
    target_lang_llm = LANGUAGES[target_lang_name][1]

    # Użyj kolumn dla przycisków
    col1_sidebar, col2_sidebar = st.columns(2)
    with col1_sidebar:
        translate_button = st.button(
            "🚀 Przetłumacz", disabled=not uploaded_file, use_container_width=True
        )
    with col2_sidebar:
        # Dodajemy przycisk Reset
        reset_button = st.button("🔄 Resetuj Stan", use_container_width=True)

    st.markdown("---")

    # Miejsce na komunikaty zwrotne
    feedback_placeholder = st.empty()

# --- Reset Logic ---
# Umieść ten blok POZA `with st.sidebar:` ale PRZED główną logiką przetwarzania
if reset_button:
    # Wyczyszczenie zmiennych stanu sesji
    keys_to_reset = ['images', 'ocr_text', 'translation_stream', 'error_message', 'success_message']
    for key in keys_to_reset:
        if key in st.session_state:
            st.session_state[key] = None
    # Wyczyszczenie miejsca na komunikaty
    feedback_placeholder.empty()
    # Odświeżenie aplikacji
    st.rerun() # Użyj st.rerun() zamiast st.experimental_rerun() w nowszych wersjach Streamlit

# --- Główny Obszar (Podział na Kolumny) ---

# Inicjalizacja zmiennych stanu poza głównym blokiem if
if 'images' not in st.session_state:
    st.session_state.images = None
if 'ocr_text' not in st.session_state:
    st.session_state.ocr_text = None
if 'translation_stream' not in st.session_state:
    st.session_state.translation_stream = None
if 'error_message' not in st.session_state:
    st.session_state.error_message = None
if 'success_message' not in st.session_state:
    st.session_state.success_message = None


col1, col2 = st.columns(2)

if translate_button and uploaded_file is not None:
    pdf_bytes = uploaded_file.getvalue()
    st.session_state.images = None # Resetuj stan przy nowym przetwarzaniu
    st.session_state.ocr_text = None
    st.session_state.translation_stream = None
    st.session_state.error_message = None
    st.session_state.success_message = None

    # Krok 1: Ekstrakcja obrazów
    with feedback_placeholder.status("Ekstrahowanie obrazów z PDF...", expanded=True) as status:
        st.session_state.images = extract_images_from_pdf(pdf_bytes)
        if not st.session_state.images:
            st.session_state.error_message = "Nie udało się wyekstrahować obrazów z pliku PDF."
            status.update(label="Błąd ekstrakcji!", state="error", expanded=True)
        else:
            status.update(label="Ekstrakcja obrazów zakończona.", state="complete", expanded=False)

    # Krok 2: OCR
    if st.session_state.images and not st.session_state.error_message:
         with feedback_placeholder.status(f"Wykonywanie OCR w języku '{ocr_lang_name}'...", expanded=True) as status:
            st.session_state.ocr_text = perform_ocr(st.session_state.images, ocr_lang_code)
            if not st.session_state.ocr_text:
                st.session_state.error_message = "Nie udało się wykonać OCR na pliku."
                status.update(label="Błąd OCR!", state="error", expanded=True)
            else:
                 status.update(label="OCR zakończony.", state="complete", expanded=False)


    # Krok 3: Tłumaczenie
    if st.session_state.ocr_text and not st.session_state.error_message:
        with feedback_placeholder.status(f"Tłumaczenie z {ocr_lang_name} na {target_lang_name}...", expanded=True) as status:
            try:
                st.session_state.translation_stream = translate_text_stream(
                    st.session_state.ocr_text, ocr_lang_name, target_lang_llm
                )
                if not st.session_state.translation_stream:
                     st.session_state.error_message = "Nie udało się rozpocząć procesu tłumaczenia (problem z API?)."
                     status.update(label="Błąd inicjalizacji tłumaczenia!", state="error", expanded=True)
                else:
                    # Symulacja zakończenia, bo stream będzie w kolumnie
                    st.session_state.success_message = "Przetwarzanie rozpoczęte." # Zmieniono komunikat
                    status.update(label="Tłumaczenie rozpoczęte.", state="complete", expanded=False) # Zmieniono status

            except Exception as e:
                 st.session_state.error_message = f"Błąd podczas komunikacji z API: {e}"
                 status.update(label="Błąd API!", state="error", expanded=True)

    # Wyświetlanie końcowych komunikatów w sidebarze
    if st.session_state.error_message:
        feedback_placeholder.error(st.session_state.error_message)
    elif st.session_state.success_message:
         # Sukces jest teraz implikowany przez obecność strumienia, komunikat wyświetlany w trakcie
         pass # Nie ma potrzeby wyświetlać "success" w sidebarze


# --- Wyświetlanie Wyników w Kolumnach ---

# --- Kolumna Lewa: Oryginalny PDF (jako obrazy) ---
with col1:
    st.subheader("📄 Oryginalny Dokument (Strony)")
    if st.session_state.images:
        pdf_container = st.container(height=700)
        with pdf_container:
            for i, img in enumerate(st.session_state.images):
                # Zmiana use_column_width na use_container_width
                st.image(img, caption=f"Strona {i+1}", use_container_width=True)
    elif uploaded_file and not st.session_state.images and not st.session_state.error_message:
         # Ten przypadek jest już obsłużony przez error message w sidebarze
         pass
    elif not uploaded_file:
        st.info("Załaduj plik PDF w pasku bocznym.")

# --- Kolumna Prawa: OCR i Tłumaczenie ---
with col2:
    st.subheader("📝 Wyniki Przetwarzania")

    if st.session_state.ocr_text:
        with st.expander("🔍 Pokaż tekst rozpoznany przez OCR", expanded=False):
            st.text_area("Tekst z OCR", st.session_state.ocr_text, height=200, disabled=True, key="ocr_output")
    elif uploaded_file and not st.session_state.images and not st.session_state.error_message:
        pass # Obsłużone w sidebarze
    elif uploaded_file and st.session_state.images and not st.session_state.ocr_text and not st.session_state.error_message:
         pass # Obsłużone w sidebarze


    if st.session_state.translation_stream:
        st.subheader("✅ Wynik Tłumaczenia:")
        try:
            output_container = st.container(height=570) # Kontener dla tłumaczenia
            with output_container:
                # Streamlit wymaga, aby `write_stream` był poza `st.status`
                # Ponieważ `translation_stream` jest generatorem, musi być konsumowany tutaj.
                full_response = st.write_stream(st.session_state.translation_stream)
                # Możemy opcjonalnie zapisać pełną odpowiedź do stanu sesji, jeśli potrzebna
                # st.session_state.full_translation = full_response
            # Wyświetl sukces PO zakończeniu streamowania
            feedback_placeholder.success("Tłumaczenie zakończone!")

        except Exception as e:
            # Błąd podczas samego streamowania
            error_msg = f"Błąd podczas streamowania odpowiedzi: {e}"
            st.error(error_msg) # Błąd wyświetlany bezpośrednio w kolumnie
            feedback_placeholder.error(error_msg) # Oraz w sidebarze
            st.session_state.error_message = error_msg # Zapisz błąd
    elif uploaded_file and st.session_state.ocr_text and not st.session_state.translation_stream and not st.session_state.error_message:
        pass # Obsłużone w sidebarze
    elif not uploaded_file:
         st.info("Wyniki pojawią się tutaj po przetworzeniu.")

