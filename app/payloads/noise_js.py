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
    return f"""
    (() => {{
        // ========================================
        // 1. CANVAS 2D NOISE (Dinamik ve Piksel Bazlı)
        // ========================================
        const getContext = HTMLCanvasElement.prototype.getContext;
        HTMLCanvasElement.prototype.getContext = function(type) {{
            const ctx = getContext.apply(this, arguments);
            if (type === '2d') {{
                const originalGetImageData = ctx.getImageData;
                ctx.getImageData = function(x, y, w, h) {{
                    const imageData = originalGetImageData.apply(this, arguments);
                    const data = imageData.data;
                    
                    // Noise map - tutarlı ama dinamik
                    const noiseMap = new Map();
                    
                    for (let i = 0; i < data.length; i += 4) {{
                        const pixelIndex = Math.floor(i / 4);
                        const x = pixelIndex % w;
                        const y = Math.floor(pixelIndex / w);
                        const key = `${{x}}_${{y}}_${{pixelIndex}}`;
                        
                        if (!noiseMap.has(key)) {{
                            noiseMap.set(key, {{
                                r: (Math.random() - 0.5) * {abs(r_shift) * 2 + 3},
                                g: (Math.random() - 0.5) * {abs(g_shift) * 2 + 3},
                                b: (Math.random() - 0.5) * {abs(b_shift) * 2 + 3}
                            }});
                        }}
                        
                        const noise = noiseMap.get(key);
                        data[i] = Math.min(255, Math.max(0, data[i] + noise.r + {r_shift}));
                        data[i+1] = Math.min(255, Math.max(0, data[i+1] + noise.g + {g_shift}));
                        data[i+2] = Math.min(255, Math.max(0, data[i+2] + noise.b + {b_shift}));
                    }}
                    return imageData;
                }};
            }}
            return ctx;
        }};

        // ========================================
        // 2. WEBGL FINGERPRINTING NOISE
        // ========================================
        const webGLGetParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(param) {{
            const result = webGLGetParameter.apply(this, arguments);
            
            // Vendor ve Renderer string'lerini standartlaştır
            if (param === this.VENDOR) {{
                return "Intel Inc.";
            }}
            if (param === this.RENDERER) {{
                return "Intel(R) UHD Graphics 620";
            }}
            if (param === this.UNMASKED_RENDERER_WEBGL) {{
                return "Intel(R) UHD Graphics 620 Direct3D11 vs_5_0 ps_5_0";
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
                    return "Intel Inc.";
                }}
                if (param === this.RENDERER) {{
                    return "Intel(R) UHD Graphics 620";
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
        // 4. FONT FINGERPRINTING KORUMASI
        // ========================================
        // Font detection API'yi manipüle et
        const originalHas = Set.prototype.has;
        Set.prototype.has = function(value) {{
            // Font check'leri için özel davranış
            if (this === document.fonts) {{
                // Standart fontları koru, diğerlerini filtrele
                const standardFonts = ['Arial', 'Times New Roman', 'Courier New', 'Verdana', 'Georgia', 'Palatino', 'Garamond', 'Bookman', 'Comic Sans MS', 'Trebuchet MS', 'Arial Black', 'Impact'];
                if (standardFonts.includes(value.family)) {{
                    return originalHas.apply(this, arguments);
                }}
                return false;
            }}
            return originalHas.apply(this, arguments);
        }};

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

    }})();
    """
