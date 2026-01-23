"""
JS Sentinel Payload
Nöbetçi script - Popup'ları ve engelleyici elementleri temizler
"""

# --- THE SENTINEL (AKILLI SÜRÜMÜ) ---
# Z-index kontrolü ile agresifliği azaltılmış sürüm
JS_SENTINEL = """
(() => {
    // 1. CSS ÖNLEME - Gelişmiş selector'lar
    const style = document.createElement('style');
    style.innerHTML = `
        [class*='popup'], [id*='popup'], [class*='modal'], [id*='modal'],
        [class*='overlay'], [id*='overlay'], [class*='banner'], [id*='banner'],
        [class*='cookie'], [id*='cookie'], [class*='sticky'], [id*='sticky'],
        [class*='reklam'], [class*='tanitim'], [class*='newsletter'],
        [data-role='modal'], [data-role='dialog'], [role='dialog'],
        [aria-modal='true'], [role='alertdialog'],
        .fancybox-overlay, .swal2-container, .sweet-alert, .bootbox,
        .modal-backdrop, .modal-overlay, .cookie-banner {
            display: none !important;
            opacity: 0 !important;
            pointer-events: none !important;
        }
        body, html { overflow: visible !important; position: static !important; }
    `;
    document.head.appendChild(style);

    // ========================================
    // YARDIMCI FONKSİYONLAR
    // ========================================

    // Önemli içerik kontrolü - ana içeriği koru
    const hasImportantContent = (el) => {
        const importantSelectors = ['main', 'article', 'section', '.content', '#content', '[role="main"]', '.main-content'];
        for (const sel of importantSelectors) {
            try {
                if (el.querySelector(sel)) return true;
            } catch (e) {}
        }
        return false;
    };

    // Z-index bazlı overlay kontrolü
    const isOverlay = (el) => {
        try {
            const style = window.getComputedStyle(el);
            const zIndex = parseInt(style.zIndex) || 0;
            const rect = el.getBoundingClientRect();
            
            // Sadece yüksek z-index ve büyük alan kaplayan elementler
            return zIndex > 100 &&
                   rect.width > window.innerWidth * 0.3 &&
                   rect.height > window.innerHeight * 0.3;
        } catch (e) {
            return false;
        }
    };

    // ========================================
    // KILL FAMILY - Akıllı ve Kontrollü
    // ========================================
    const killFamily = (el) => {
        let current = el;
        let killed = false;
        
        // 5 seviye yukarı çık ama BODY ve HTML'yi geçme
        for (let i = 0; i < 5; i++) {
            if (!current || current.tagName === 'BODY' || current.tagName === 'HTML') break;
            
            const style = window.getComputedStyle(current);
            const rect = current.getBoundingClientRect();
            
            // Z-index ve içerik kontrolü
            if ((style.position === 'fixed' || style.position === 'absolute') &&
                !hasImportantContent(current)) {
                
                // Z-index kontrolü - çok yüksekse overlay olabilir
                const zIndex = parseInt(style.zIndex) || 0;
                
                // Boyut kontrolü - çok büyükse silme (ana içerik olabilir)
                const isTooBig = rect.width > window.innerWidth * 0.8 &&
                                 rect.height > window.innerHeight * 0.8;
                
                // Küçük veya orta boy elementleri sil
                if (!isTooBig || zIndex > 100) {
                    console.log('Popup Silindi:', current.className || current.id);
                    current.style.display = 'none'; // remove yerine display:none
                    killed = true;
                    break;
                }
            }
            current = current.parentElement;
        }
        
        // Eğer hiçbir ata silinmediyse, en azından kendisini gizle
        if (!killed) {
            el.style.display = 'none';
        }
    };

    // ========================================
    // 2. TEMİZLİK FONKSİYONU - Gelişmiş
    // ========================================
    const cleanUp = () => {
        const h = window.innerHeight;
        const w = window.innerWidth;
        const keywords = ['güncel adres', 'bahis', 'yatırım', 'bonus', 'hoşgeldin', 'kapat', 'giriş', 'twitter', 'telegram', 'her daim'];

        document.querySelectorAll('*').forEach(el => {
            try {
                if (el.offsetParent === null) return; // Görünmezse geç
                
                const style = window.getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                const txt = el.innerText.toLowerCase();

                // A) "X" VEYA "KAPAT" BUTONU BULUCU
                // Küçük kutu + içinde X veya Close varsa -> AİLESİNİ YOK ET
                if (rect.width < 60 && rect.height < 60) {
                    if (txt === 'x' || txt === '×' || txt === '✕' || txt.includes('kapat') || txt.includes('close')) {
                        killFamily(el);
                        return;
                    }
                }

                // B) YASAKLI KELİME AVCI - Z-index kontrolü ile
                // Eğer element sabitse, yüksek z-index'e sahipse ve içinde bahis kelimeleri geçiyorsa
                const zIndex = parseInt(style.zIndex) || 0;
                if ((style.position === 'fixed' || style.position === 'absolute') &&
                    rect.width > 50 && rect.height > 50 &&
                    zIndex > 50) {
                     if (keywords.some(kw => txt.includes(kw))) {
                         console.log('Yasaklı Kelime:', txt.substring(0, 20));
                         el.style.display = 'none';
                         return;
                     }
                }

                // C) BOŞ KUTU ÇÖPÇÜSÜ - Z-index kontrolü ile
                // Sabit, büyük, ama içinde az metin var veya içi boşaltılmış
                if (style.position === 'fixed' &&
                    rect.height > 100 && rect.width > 50 &&
                    zIndex > 50) {
                    // Header değilse (Header genelde incedir ve en tepededir)
                    if (!(rect.top === 0 && rect.height < 80)) {
                         // Eğer içi boşsa veya sadece renk varsa
                         if (el.innerText.trim().length < 5) {
                             console.log('Boş Kutu Silindi:', el);
                             el.style.display = 'none';
                         }
                    }
                }

                // D) GEOMETRİK AV (Yan Bantlar) - Z-index kontrolü ile
                if (style.position === 'fixed' || style.position === 'absolute') {
                    const zIndexVal = parseInt(style.zIndex) || 0;
                    
                    // Sadece yüksek z-index'li elementleri kontrol et
                    if (zIndexVal > 50) {
                        // Dikey Yan Bant
                        if (rect.height > h * 0.6 && rect.width < w * 0.4) {
                            el.style.display = 'none';
                        }
                        // Tam Ekran Overlay
                        if (rect.width > w * 0.9 && rect.height > h * 0.9) {
                            el.style.display = 'none';
                        }
                    }
                }

            } catch(e) {}
        });
        document.body.style.overflow = 'visible';
    };

    // ========================================
    // 3. SÜREKLİ TAKİP - Performans Optimizasyonu
    // ========================================
    
    // Interval'i 400ms -> 1000ms azalttık (CPU kullanımını düşürmek için)
    let lastCleanup = 0;
    const cleanupInterval = 1000;
    
    const smartCleanUp = () => {
        const now = Date.now();
        if (now - lastCleanup < cleanupInterval) return;
        lastCleanup = now;
        
        requestAnimationFrame(cleanUp);
    };
    
    // Debounce'li MutationObserver
    let observerTimeout;
    const debouncedObserver = () => {
        clearTimeout(observerTimeout);
        observerTimeout = setTimeout(cleanUp, 500);
    };
    
    // Ana cleanup interval
    setInterval(smartCleanUp, cleanupInterval);
    
    // MutationObserver ile DOM değişikliklerini izle
    const observer = new MutationObserver(debouncedObserver);
    observer.observe(document.body, { childList: true, subtree: true });

    // İlk çalıştırma
    setTimeout(cleanUp, 100);
})();
"""
