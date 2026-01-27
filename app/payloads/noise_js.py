"""
Canvas Noise JavaScript Payload
Tutarlı canvas gürültüsü oluşturur
"""


def get_consistent_noise_js(r_shift: int, g_shift: int, b_shift: int) -> str:
    """
    Tutarlı canvas gürültüsü JavaScript kodu döndürür.
    Canvas, WebGL ve Audio fingerprinting'i hedef alır.

    Args:
        r_shift: Kırmızı kanal kayma değeri
        g_shift: Yeşil kanal kayma değeri
        b_shift: Mavi kanal kayma değeri

    Returns:
        JavaScript kodu string olarak
    """
    # Python tarafında hesaplamaları yap (JS içinde abs() hatası almamak için)
    r_factor = abs(r_shift) * 2 + 3
    g_factor = abs(g_shift) * 2 + 3
    b_factor = abs(b_shift) * 2 + 3
    
    # WebGL varyasyonları için seed değerleri oluştur (Hata #13 düzeltmesi)
    vendor_seed = abs(r_shift) % 3
    renderer_seed = abs(g_shift) % 3
    
    # WebGL vendor seçenekleri
    vendor_options = [
        "Intel Inc.",
        "NVIDIA Corporation",
        "AMD"
    ]
    
    # WebGL renderer seçenekleri
    renderer_options = [
        "Intel(R) UHD Graphics 620",
        "NVIDIA GeForce GTX 1650",
        "AMD Radeon RX 580"
    ]
    
    vendor = vendor_options[vendor_seed]
    renderer = renderer_options[renderer_seed]

    return f"""
    (function() {{
        // Değerler Python'dan hazır geliyor
        const shift = {{ r: {r_shift}, g: {g_shift}, b: {b_shift} }};
        const factor = {{ r: {r_factor}, g: {g_factor}, b: {b_factor} }};

        // ========================================
        // 1. CANVAS 2D NOISE (Dinamik ve Piksel Bazlı)
        // ========================================
        const originalGetContext = HTMLCanvasElement.prototype.getContext;
        HTMLCanvasElement.prototype.getContext = function(type, options) {{
            const context = originalGetContext.call(this, type, options);

            if (context && (type === '2d' || type === 'webgl' || type === 'experimental-webgl')) {{
                const originalGetImageData = context.getImageData;
                context.getImageData = function(x, y, w, h) {{
                    const imageData = originalGetImageData.call(this, x, y, w, h);
                    const data = imageData.data;
                    const noiseMap = new Map(); // Performans için cache

                    for (let i = 0; i < data.length; i += 4) {{
                        // Piksel koordinatına göre key üret
                        const pixelIndex = Math.floor(i / 4);
                        const px = pixelIndex % w;
                        const py = Math.floor(pixelIndex / w);
                        const key = `${{px}}_${{py}}_${{pixelIndex}}`;

                        if (!noiseMap.has(key)) {{
                            noiseMap.set(key, {{
                                r: (Math.random() - 0.5) * factor.r,
                                g: (Math.random() - 0.5) * factor.g,
                                b: (Math.random() - 0.5) * factor.b
                            }});
                        }}

                        const noise = noiseMap.get(key);
                        // Renkleri kaydır ve 0-255 sınırında tut
                        data[i] = Math.min(255, Math.max(0, data[i] + noise.r + shift.r));
                        data[i+1] = Math.min(255, Math.max(0, data[i+1] + noise.g + shift.g));
                        data[i+2] = Math.min(255, Math.max(0, data[i+2] + noise.b + shift.b));
                    }}
                    return imageData;
                }};
            }}
            return context;
        }};

        // ========================================
        // 2. WEBGL FINGERPRINTING NOISE
        // ========================================
        const webGLGetParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(param) {{
            const result = webGLGetParameter.apply(this, arguments);

            // Vendor ve Renderer string'lerini varyasyonlu yap (Hata #13 düzeltmesi)
            if (param === this.VENDOR) {{
                return "{vendor}";
            }}
            if (param === this.RENDERER) {{
                return "{renderer}";
            }}
            if (param === this.UNMASKED_RENDERER_WEBGL) {{
                return "{renderer} Direct3D11 vs_5_0 ps_5_0";
            }}

            // Max texture size ve diğer parametreleri hafifçe değiştir
            if (param === this.MAX_TEXTURE_SIZE) {{
                return result - Math.floor(Math.random() * 100);
            }}
            if (param === this.MAX_VIEWPORT_DIMS) {{
                return [result[0] - Math.floor(Math.random() * 10), result[1] - Math.floor(Math.random() * 10)];
            }}

            return result;
        }};

        // WebGL2 için de aynı koruma
        if (typeof WebGL2RenderingContext !== 'undefined') {{
            const webGL2GetParameter = WebGL2RenderingContext.prototype.getParameter;
            WebGL2RenderingContext.prototype.getParameter = function(param) {{
                const result = webGL2GetParameter.apply(this, arguments);

                if (param === this.VENDOR) {{
                    return "{vendor}";
                }}
                if (param === this.RENDERER) {{
                    return "{renderer}";
                }}

                return result;
            }};
        }}

        // ========================================
        // 3. AUDIO FINGERPRINTING NOISE
        // ========================================
        const audioGetChannelData = AudioBuffer.prototype.getChannelData;
        AudioBuffer.prototype.getChannelData = function(channel) {{
            const result = audioGetChannelData.apply(this, arguments);

            // Her sample'a çok küçük noise ekle
            for (let i = 0; i < result.length; i++) {{
                result[i] = result[i] + (Math.random() - 0.5) * 0.0001;
            }}

            return result;
        }};

        // AudioContext sampleRate değişimi
        const originalCreateAnalyser = AudioContext.prototype.createAnalyser;
        AudioContext.prototype.createAnalyser = function() {{
            const analyser = originalCreateAnalyser.apply(this, arguments);
            const originalGetFloatFrequencyData = analyser.getFloatFrequencyData;

            analyser.getFloatFrequencyData = function(array) {{
                originalGetFloatFrequencyData.apply(this, arguments);
                for (let i = 0; i < array.length; i++) {{
                    array[i] = array[i] + (Math.random() - 0.5) * 0.001;
                }}
            }};

            return analyser;
        }};

        // ========================================
        // 4. FONT FINGERPRINTING KORUMASI (Safe Mode)
        // ========================================
        // Sadece document.fonts nesnesini hedefliyoruz, tüm Set'leri değil.
        if (document.fonts) {{
            const standardFonts = ['Arial', 'Times New Roman', 'Courier New', 'Verdana', 'Georgia', 'Palatino', 'Garamond', 'Bookman', 'Comic Sans MS', 'Trebuchet MS', 'Arial Black', 'Impact'];

            // 4a. document.fonts.has override
            const originalFontsHas = document.fonts.has;
            document.fonts.has = function(value) {{
                if (value && value.family && standardFonts.includes(value.family)) {{
                    return originalFontsHas.apply(this, arguments);
                }}
                return false; // Standart dışı fontları gizle
            }};

            // 4b. document.fonts.check override
            const originalFontsCheck = document.fonts.check;
            document.fonts.check = function(font) {{
                // Font string içinde standart fontlardan biri geçiyor mu?
                for (const std of standardFonts) {{
                    if (font.includes(std)) return true;
                }}
                return originalFontsCheck.apply(this, arguments);
            }};
        }}

        // ========================================
        // 5. SCREEN VE DISPLAY MANİPÜLASYONU
        // ========================================
        // Screen resolution değerlerini hafifçe değiştir
        const screenProps = ['availWidth', 'availHeight', 'width', 'height', 'colorDepth', 'pixelDepth'];
        screenProps.forEach(prop => {{
            const originalValue = screen[prop];
            if (prop === 'colorDepth' || prop === 'pixelDepth') {{
                Object.defineProperty(screen, prop, {{
                    get: () => 24
                }});
            }} else if (prop === 'width') {{
                Object.defineProperty(screen, prop, {{
                    get: () => originalValue - Math.floor(Math.random() * 10)
                }});
            }} else if (prop === 'height') {{
                Object.defineProperty(screen, prop, {{
                    get: () => originalValue - Math.floor(Math.random() * 10)
                }});
            }}
        }});

        console.log("🛡️ Anti-Fingerprint v2 (Safe Mode) aktif.");
    }})();
    """
