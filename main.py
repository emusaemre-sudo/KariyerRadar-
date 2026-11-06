import json
import flet as ft
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# --- KAZIMA (SCRAPING) MOTORLARI ---
def fetch_resmi_gazete():
    """Bugünün Resmî Gazete fihristini tarar."""
    rg_ads = {"academic": [], "civil": []}
    
    today = datetime.now()
    year = today.strftime("%Y")
    month = today.strftime("%m")
    day = today.strftime("%d")
    date_str = f"{year}{month}{day}"
    
    url_rg = f"https://www.resmigazete.gov.tr/eskiler/{year}/{month}/{date_str}.htm"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        resp = requests.get(url_rg, headers=headers, timeout=10)
        resp.encoding = 'utf-8'
        
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            for a_tag in soup.find_all('a', href=True):
                title = a_tag.text.strip()
                title_lower = title.lower()
                link = a_tag['href']
                if not link.startswith('http'):
                    link = f"https://www.resmigazete.gov.tr/eskiler/{year}/{month}/{link}"
                
                # 1. Akademik İlanlar
                if "üniversite" in title_lower or "rektörlüğünden" in title_lower:
                    rg_ads["academic"].append({
                        "title": title,
                        "source": "Resmî Gazete (Akademik)",
                        "link": link,
                        "icon": ft.icons.ACCOUNT_BALANCE,
                        "color": ft.colors.BLUE_200
                    })
                
                # 2. Memurluk İlanları (FİLTRESİZ)
                elif "bakanlığından" in title_lower or "belediye" in title_lower or "memur" in title_lower or "personel" in title_lower or "kurumu" in title_lower or "başkanlığı" in title_lower:
                    rg_ads["civil"].append({
                        "title": title,
                        "source": "Resmî Gazete (Genel Kadro)",
                        "link": link,
                        "icon": ft.icons.ACCOUNT_BALANCE,
                        "color": ft.colors.AMBER_200
                    })
    except Exception as e:
        print(f"Resmî Gazete Kazıma Hatası: {e}")
        
    return rg_ads

def fetch_memurlar_net():
    """Memurlar.net havuzunu tarar."""
    mn_ads = {"academic": [], "civil": []}
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    # 1. Memurluk (FİLTRESİZ)
    try:
        url_civil = "https://ilan.memurlar.net/kategori/kpss-b-ilanlari/?Expire=false"
        resp = requests.get(url_civil, headers=headers, timeout=10)
        resp.encoding = 'windows-1254'
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        for a_tag in soup.find_all('a', href=True):
            title = a_tag.text.strip()
            link = a_tag['href']
            
            if not link.startswith('/ilan/') or len(title) < 15:
                continue
                
            full_link = "https://ilan.memurlar.net" + link if not link.startswith('http') else link
            title_lower = title.lower()
            
            # Sadece site menülerini (çöpleri) engelliyoruz, geri kalan TÜM ilanları alıyoruz
            if "hesaplama" in title_lower or "ortak konular" in title_lower or "maaş" in title_lower or "soru cevap" in title_lower:
                continue
                
            if not any(ad['title'] == title for ad in mn_ads["civil"]):
                mn_ads["civil"].append({
                    "title": title,
                    "source": "Memurlar.net",
                    "link": full_link,
                    "icon": ft.icons.WORK,
                    "color": ft.colors.AMBER_400
                })
    except Exception as e:
         print(f"Memurlar.net Memurluk Hatası: {e}")

    # 2. Akademi (SADECE MATEMATİK + ARŞ. GÖR.)
    try:
        url_academic = "https://ilan.memurlar.net/kategori/akademik-personel-ilanlari/?Expire=false"
        resp = requests.get(url_academic, headers=headers, timeout=10)
        resp.encoding = 'windows-1254'
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        for a_tag in soup.find_all('a', href=True):
            title = a_tag.text.strip()
            link = a_tag['href']
            
            if not link.startswith('/ilan/') or len(title) < 15:
                continue
                
            full_link = "https://ilan.memurlar.net" + link if not link.startswith('http') else link
            title_lower = title.lower()
            
            if ("araştırma görevlisi" in title_lower or "arş. gör" in title_lower) and "matematik" in title_lower:
                if not any(ad['title'] == title for ad in mn_ads["academic"]):
                    mn_ads["academic"].append({
                        "title": title,
                        "source": "Memurlar.net",
                        "link": full_link,
                        "icon": ft.icons.SCHOOL,
                        "color": ft.colors.BLUE_400
                    })
    except Exception as e:
        print(f"Memurlar.net Akademi Hatası: {e}")

    return mn_ads

# --- ARAYÜZ (FLET) ---
def main(page: ft.Page):
    page.title = "Kariyer Radarı"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 400
    page.window_height = 800
    page.padding = 0
    page.bgcolor = "#0F172A" 
    
    academic_list = ft.ListView(expand=True, spacing=10, padding=15)
    civil_list = ft.ListView(expand=True, spacing=10, padding=15)

    try:
        ad_statuses = json.loads(page.client_storage.get("kariyer_radar_ad_statuses") or "{}")
    except Exception:
        ad_statuses = {}

    def save_ad_status(link, viewed, decision):
        ad_statuses[link] = {"viewed": viewed, "decision": decision}
        page.client_storage.set("kariyer_radar_ad_statuses", json.dumps(ad_statuses, ensure_ascii=False))

    def create_ad_card(title, source, link, icon_name, color):
        saved = ad_statuses.get(link, {})
        viewed_value = bool(saved.get("viewed", False))
        decision_value = saved.get("decision", "Karar bekliyor")

        def decision_color(value):
            if value == "Başvuruya uygun":
                return "#14532D"
            if value == "Uygun değil":
                return "#7F1D1D"
            return "#334155"

        status_badge = ft.Container(
            content=ft.Text(decision_value, size=11, color=ft.colors.WHITE, weight=ft.FontWeight.BOLD),
            bgcolor=decision_color(decision_value),
            padding=ft.padding.symmetric(horizontal=10, vertical=6),
            border_radius=12,
        )

        viewed_checkbox = ft.Checkbox(
            label="İnceledim",
            value=viewed_value,
            active_color=ft.colors.INDIGO_400,
            on_change=lambda e: save_ad_status(link, e.control.value, decision_dropdown.value),
        )

        def on_decision_change(e):
            selected = e.control.value
            save_ad_status(link, viewed_checkbox.value, selected)
            status_badge.content = ft.Text(selected, size=11, color=ft.colors.WHITE, weight=ft.FontWeight.BOLD)
            status_badge.bgcolor = decision_color(selected)
            page.update()

        decision_dropdown = ft.Dropdown(
            label="Başvuru durumu",
            width=190,
            value=decision_value,
            options=[
                ft.dropdown.Option("Karar bekliyor"),
                ft.dropdown.Option("Başvuruya uygun"),
                ft.dropdown.Option("Uygun değil"),
            ],
            on_change=on_decision_change,
        )

        return ft.Card(
            elevation=4,
            color="#1E293B",
            content=ft.Container(
                padding=15,
                content=ft.Column(
                    [
                        ft.ListTile(
                            leading=ft.Icon(icon_name, color=color, size=30),
                            title=ft.Text(title, weight=ft.FontWeight.BOLD, size=14),
                            subtitle=ft.Text(f"Kaynak: {source}", color=ft.colors.GREY_400, size=12),
                            content_padding=0,
                        ),
                        ft.Divider(height=1, color="#334155"),
                        ft.Row(
                            [
                                viewed_checkbox,
                                decision_dropdown,
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Row(
                            [
                                ft.Row(
                                    [
                                        ft.Icon(ft.icons.CHECK_CIRCLE, size=16, color=ft.colors.GREEN_400),
                                        ft.Text("Aktif İlan", size=12, color=ft.colors.GREEN_400),
                                    ],
                                    spacing=5,
                                ),
                                status_badge,
                                ft.ElevatedButton(
                                    "İlana Git",
                                    icon=ft.icons.LINK,
                                    url=link,
                                    style=ft.ButtonStyle(
                                        color=color,
                                        bgcolor="#0F172A",
                                        shape=ft.RoundedRectangleBorder(radius=8),
                                    ),
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ],
                    spacing=10,
                ),
            ),
        )

    def scan_ads(e):
        scan_btn.content = ft.Row([ft.ProgressRing(width=20, height=20, color=ft.colors.WHITE), ft.Text("İlanlar Hızla Çekiliyor...", weight=ft.FontWeight.BOLD)], alignment=ft.MainAxisAlignment.CENTER)
        scan_btn.disabled = True
        page.update()

        rg_data = fetch_resmi_gazete()
        mn_data = fetch_memurlar_net()
        
        all_academic = rg_data["academic"] + mn_data["academic"]
        all_civil = rg_data["civil"] + mn_data["civil"]
        
        academic_list.controls.clear()
        civil_list.controls.clear()

        for ad in all_academic:
            academic_list.controls.append(create_ad_card(ad["title"], ad["source"], ad["link"], ad["icon"], ad["color"]))
            
        for ad in all_civil:
            civil_list.controls.append(create_ad_card(ad["title"], ad["source"], ad["link"], ad["icon"], ad["color"]))

        if not all_academic:
            academic_list.controls.append(ft.Text("Şu an kriterlerine uygun Matematik Arş. Gör. ilanı yok.", color=ft.colors.GREY_500))
        if not all_civil:
            civil_list.controls.append(ft.Text("Şu an sistemde aktif ilan bulunamadı.", color=ft.colors.GREY_500))

        scan_btn.content = ft.Row([ft.Icon(ft.icons.RADAR), ft.Text("İlanları Yenile", weight=ft.FontWeight.BOLD)], alignment=ft.MainAxisAlignment.CENTER)
        scan_btn.disabled = False
        
        total_found = len(all_academic) + len(all_civil)
        page.snack_bar = ft.SnackBar(ft.Text(f"Tarama tamamlandı! {total_found} ilan listelendi."), bgcolor=ft.colors.GREEN_800)
        page.snack_bar.open = True
        page.update()

    scan_btn = ft.ElevatedButton(
        content=ft.Row([ft.Icon(ft.icons.RADAR), ft.Text("İlanları Tara", weight=ft.FontWeight.BOLD)], alignment=ft.MainAxisAlignment.CENTER),
        width=330,
        height=50,
        style=ft.ButtonStyle(
            bgcolor=ft.colors.INDIGO_600,
            color=ft.colors.WHITE,
            shape=ft.RoundedRectangleBorder(radius=25)
        ),
        on_click=scan_ads
    )

    header = ft.Container(
        padding=ft.padding.only(left=18, right=18, top=18, bottom=10),
        content=ft.Row(
            [
                ft.Container(
                    width=52,
                    height=52,
                    bgcolor="#172554",
                    border_radius=16,
                    alignment=ft.alignment.center,
                    content=ft.Icon(ft.icons.RADAR, color="#67E8F9", size=34),
                ),
                ft.Column(
                    [
                        ft.Text("KARİYER RADARI", size=18, weight=ft.FontWeight.BOLD, color=ft.colors.WHITE),
                        ft.Text("Fırsatları keşfet, başvurunu takip et", size=11, color=ft.colors.BLUE_200),
                    ],
                    spacing=2,
                ),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        unselected_label_color=ft.colors.GREY_500,
        label_color=ft.colors.WHITE,
        indicator_color=ft.colors.INDIGO_400,
        tabs=[
            ft.Tab(
                text="Memurluk", 
                icon=ft.icons.WORK,
                content=civil_list,
            ),
            ft.Tab(
                text="Akademi",
                icon=ft.icons.MENU_BOOK,
                content=academic_list,
            ),
        ],
        expand=True,
    )

    page.add(
        header,
        tabs,
        ft.Container(
            content=scan_btn,
            alignment=ft.alignment.center,
            padding=ft.padding.only(left=16, right=16, top=10, bottom=16),
        ),
    )

ft.app(target=main)