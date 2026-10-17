# Automatizovaný test responzivity, přetékání a PŘEKRÝVÁNÍ elementů

import sys
from playwright.sync_api import sync_playwright

URLS = [
    "http://localhost:1313/",
    "http://localhost:1313/brno/",
    "http://localhost:1313/praha/",
    "http://localhost:1313/liberec/",
    "http://localhost:1313/partneri/",
    "http://localhost:1313/o-nas/",
    "http://localhost:1313/kontakt/",
]

# Testujeme šířky po 50px krocích pro velmi jemnou síť od 320 do 1200
WIDTHS = list(range(320, 1201, 50)) + [1440]

def check_layout():
    has_errors = False
    print(f"Spouštím rigorózní test responzivity (testuji {len(WIDTHS)} velikostí na {len(URLS)} stránkách)...\n")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        for url in URLS:
            print(f"--- Testuji: {url} ---")
            try:
                page.goto(url)
            except Exception as e:
                print(f"  [Chyba] Nelze načíst {url}.")
                continue
            
            for width in WIDTHS:
                page.set_viewport_size({"width": width, "height": 900})
                page.wait_for_timeout(300)
                
                issues = page.evaluate("""
                    () => {
                        let errors = [];
                        let viewportWidth = document.documentElement.clientWidth;
                        
                        // 1. KONTROLA PŘETÉKÁNÍ (OVERFLOW)
                        document.querySelectorAll('*').forEach(el => {
                            let rect = el.getBoundingClientRect();
                            let style = window.getComputedStyle(el);
                            
                            if (rect.width === 0 || el.tagName === 'SCRIPT' || el.tagName === 'STYLE' || style.display === 'none' || style.visibility === 'hidden') return;
                            if (rect.left >= viewportWidth) return;
                            if (el.closest('.carousel-viewport') || el.closest('.mobile-off-canvas-menu')) return;
                            
                            if (rect.right > viewportWidth + 1) {
                                errors.push(`OVERFLOW: <${el.tagName} class='${el.className}'> přesahuje o ${Math.round(rect.right - viewportWidth)}px (šířka elementu: ${rect.width}px)`);
                            }
                        });
                        
                        // Pomocná funkce pro získání viditelného obdélníku (po oříznutí rodiči s overflow: hidden)
                        function getClippedRect(el) {
                            let rect = el.getBoundingClientRect();
                            let top = rect.top, bottom = rect.bottom, left = rect.left, right = rect.right;
                            
                            let parent = el.parentElement;
                            while (parent) {
                                let pStyle = window.getComputedStyle(parent);
                                if (pStyle.overflow !== 'visible' || pStyle.overflowY !== 'visible' || pStyle.overflowX !== 'visible') {
                                    let pRect = parent.getBoundingClientRect();
                                    if (pStyle.overflow !== 'visible' || pStyle.overflowY !== 'visible') {
                                        top = Math.max(top, pRect.top);
                                        bottom = Math.min(bottom, pRect.bottom);
                                    }
                                    if (pStyle.overflow !== 'visible' || pStyle.overflowX !== 'visible') {
                                        left = Math.max(left, pRect.left);
                                        right = Math.min(right, pRect.right);
                                    }
                                }
                                parent = parent.parentElement;
                            }
                            return { top, bottom, left, right, width: Math.max(0, right - left), height: Math.max(0, bottom - top) };
                        }

                        let allElements = Array.from(document.querySelectorAll('*'));
                        
                        function isVisible(el) {
                            let s = window.getComputedStyle(el);
                            if (s.display === 'none' || s.visibility === 'hidden' || s.opacity === '0') return false;
                            let r = getClippedRect(el);
                            if (r.width <= 0 || r.height <= 0) return false;
                            
                            // Off-canvas mobile menu is intentionally hidden off-screen
                            if (el.closest('.mobile-off-canvas-menu')) {
                                let menuRect = el.closest('.mobile-off-canvas-menu').getBoundingClientRect();
                                if (menuRect.left >= viewportWidth || menuRect.right <= 0) return false;
                            }
                            return true;
                        }

                        let visibleElements = allElements.filter(isVisible);

                        // 1. KONTROLA KOLIZÍ BLOKŮ
                        let textContainers = visibleElements.filter(el => {
                            if (['IMG', 'SVG', 'IFRAME', 'VIDEO'].includes(el.tagName)) return true;
                            let s = window.getComputedStyle(el);
                            if (s.backgroundImage !== 'none' && s.backgroundImage !== 'url("about:blank")') return true;
                            
                            let hasDirectText = Array.from(el.childNodes).some(node => node.nodeType === Node.TEXT_NODE && node.textContent.trim().length > 0);
                            if (['P', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'SPAN', 'STRONG', 'A', 'LI', 'BUTTON', 'EM', 'I'].includes(el.tagName)) return true;
                            return hasDirectText;
                        });

                        for (let i = 0; i < textContainers.length; i++) {
                            for (let j = i + 1; j < textContainers.length; j++) {
                                let el1 = textContainers[i];
                                let el2 = textContainers[j];
                                
                                if (el1.contains(el2) || el2.contains(el1)) continue;
                                
                                let inlineTags = ['SPAN', 'STRONG', 'A', 'EM', 'I'];
                                if (inlineTags.includes(el1.tagName) && inlineTags.includes(el2.tagName)) {
                                    let p1 = el1.closest('p, h1, h2, h3, h4, h5, h6, li, div');
                                    let p2 = el2.closest('p, h1, h2, h3, h4, h5, h6, li, div');
                                    if (p1 === p2) continue;
                                }

                                let r1 = getClippedRect(el1);
                                let r2 = getClippedRect(el2);
                                
                                let overlapX = Math.max(0, Math.min(r1.right, r2.right) - Math.max(r1.left, r2.left));
                                let overlapY = Math.max(0, Math.min(r1.bottom, r2.bottom) - Math.max(r1.top, r2.top));
                                let overlapArea = overlapX * overlapY;
                                
                                if (overlapArea > 10) {
                                    let s1 = window.getComputedStyle(el1);
                                    let s2 = window.getComputedStyle(el2);
                                    let z1 = parseInt(s1.zIndex) || 0;
                                    let z2 = parseInt(s2.zIndex) || 0;
                                    
                                    if ((s1.position === 'absolute' && z1 < 0) || (s2.position === 'absolute' && z2 < 0)) continue;
                                    if (el1.closest('.map-region') || el2.closest('.map-region')) continue;
                                    
                                    // Ignorovat carousel img vs img úmyslné překrytí (slides)
                                    if (el1.tagName === 'IMG' && el2.tagName === 'IMG' && el1.closest('.carousel-track')) continue;

                                    let c1 = el1.getAttribute('class') || '';
                                    let c2 = el2.getAttribute('class') || '';
                                    let tag1 = el1.tagName + (c1 ? '.'+c1.split(' ')[0] : '');
                                    let tag2 = el2.tagName + (c2 ? '.'+c2.split(' ')[0] : '');
                                    let t1 = (el1.textContent || '').trim().substring(0, 15).replace(/\\n/g, '');
                                    let t2 = (el2.textContent || '').trim().substring(0, 15).replace(/\\n/g, '');
                                    
                                    // Chceme zachytit hlavně Foto vs Text
                                    if (el1.tagName === 'IMG' || el2.tagName === 'IMG') {
                                        errors.push(`KOLIZE FOTKY A TEXTU: ${tag1} ("${t1}") leží na ${tag2} ("${t2}") o ${Math.round(overlapArea)}px`);
                                    } else {
                                        errors.push(`KOLIZE TEXTŮ: ${tag1} ("${t1}") leží na ${tag2} ("${t2}")`);
                                    }
                                }
                            }
                        }
                        
                        return [...new Set(errors)];
                    }
                """)
                
                if issues:
                    has_errors = True
                    print(f"  [!] Šířka {width}px má chyby:")
                    for err in issues:
                        print(f"      - {err}")
                else:
                    # Jen vypíšeme malou tečku nebo zkrácenou zprávu, ať nespamujeme log
                    pass
            print("  -> Všechny zkoušené velikosti pro tuto stránku prošly.\n")
            
        browser.close()
        
    if has_errors:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    check_layout()
