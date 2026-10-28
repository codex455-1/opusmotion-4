class Post {
  constructor(canvas) {
    this.canvas = canvas;
    this.gl = canvas.getContext("webgl2", { preserveDrawingBuffer: true, antialias: false, alpha: false });
    const gl = this.gl;
    if (!gl) throw new Error("WebGL2 unavailable");
    this.quad = this.makeQuad();
    this.sceneTex = this.texture();
    this.grainTex = [];
    this.noiseTex = this.texture();
    this.fbo = {};
    this.progBright = this.program(VS, FS_BRIGHT);
    this.progBlur = this.program(VS, FS_BLUR);
    this.progComp = this.program(VS, FS_COMP);
    this.resize(canvas.width, canvas.height);
  }
  texture() {
    const gl = this.gl, t = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, t);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    return t;
  }
  makeQuad() {
    const gl = this.gl, b = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, b);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
    return b;
  }
  program(vs, fs) {
    const gl = this.gl;
    const sh = (type, src) => {
      const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
      return s;
    };
    const p = gl.createProgram();
    gl.attachShader(p, sh(gl.VERTEX_SHADER, vs));
    gl.attachShader(p, sh(gl.FRAGMENT_SHADER, fs));
    gl.linkProgram(p);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p));
    return p;
  }
  resize(w, h) {
    const gl = this.gl;
    this.w = w; this.h = h;
    for (const k in this.fbo) { gl.deleteFramebuffer(this.fbo[k].fb); gl.deleteTexture(this.fbo[k].tex); }
    this.fbo = {};
    const mk = (name, fw, fh) => {
      const tex = this.texture();
      gl.bindTexture(gl.TEXTURE_2D, tex);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, fw, fh, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
      const fb = gl.createFramebuffer();
      gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
      gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
      this.fbo[name] = { fb, tex, w: fw, h: fh };
    };
    mk("bright", Math.round(w / 2), Math.round(h / 2));
    mk("blurA", Math.round(w / 2), Math.round(h / 2));
    mk("blurB", Math.round(w / 2), Math.round(h / 2));
  }
  bindTex(unit, tex) { const gl = this.gl; gl.activeTexture(gl.TEXTURE0 + unit); gl.bindTexture(gl.TEXTURE_2D, tex); return unit; }
  draw(prog, target, uniforms = {}) {
    const gl = this.gl;
    gl.bindFramebuffer(gl.FRAMEBUFFER, target ? this.fbo[target].fb : null);
    const tw = target ? this.fbo[target].w : this.w, th = target ? this.fbo[target].h : this.h;
    gl.viewport(0, 0, tw, th);
    gl.useProgram(prog);
    const loc = gl.getAttribLocation(prog, "p");
    gl.bindBuffer(gl.ARRAY_BUFFER, this.quad);
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
    for (const k in uniforms) {
      const u = gl.getUniformLocation(prog, k);
      if (!u) continue;
      const v = uniforms[k];
      if (typeof v === "number") {
        if (k.startsWith("uTex") || k === "uScene" || k === "uBloom" || k === "uGrain" || k === "uNoise") gl.uniform1i(u, v);
        else gl.uniform1f(u, v);
      } else if (v.length === 2) gl.uniform2f(u, v[0], v[1]);
      else if (v.length === 3) gl.uniform3f(u, v[0], v[1], v[2]);
      else if (v.length === 4) gl.uniform4f(u, v[0], v[1], v[2], v[3]);
    }
    gl.drawArrays(gl.TRIANGLES, 0, 3);
  }
  upload(source) {
    const gl = this.gl;
    gl.bindTexture(gl.TEXTURE_2D, this.sceneTex);
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, gl.RGBA, gl.UNSIGNED_BYTE, source);
  }
  setGrain(images) {
    const gl = this.gl;
    this.grainTex = images.map(img => {
      const t = this.texture(); gl.bindTexture(gl.TEXTURE_2D, t);
      gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, gl.RGBA, gl.UNSIGNED_BYTE, img); return t;
    });
  }
  render(source, time, mood = {}) {
    const gl = this.gl;
    this.upload(source);
    // bright pass
    gl.disable(gl.BLEND);
    this.bindTex(0, this.sceneTex);
    this.draw(this.progBright, "bright", { uScene: 0, uTexel: [1 / this.w, 1 / this.h], uThreshold: mood.threshold == null ? .62 : mood.threshold });
    // blur
    for (let i = 0; i < 2; i++) {
      this.bindTex(0, i === 0 ? this.fbo.bright.tex : this.fbo.blurB.tex);
      this.draw(this.progBlur, "blurA", { uScene: 0, uTexel: [1 / this.fbo.bright.w, 0], uDir: [1, 0], uRadius: 1.5 + i * 1.4 });
      this.bindTex(0, this.fbo.blurA.tex);
      this.draw(this.progBlur, "blurB", { uScene: 0, uTexel: [0, 1 / this.fbo.bright.h], uDir: [0, 1], uRadius: 1.5 + i * 1.4 });
    }
    const g = this.grainTex.length ? this.grainTex[Math.floor(time * 24) % this.grainTex.length] : null;
    this.bindTex(0, this.sceneTex);
    this.bindTex(1, this.fbo.blurB.tex);
    this.bindTex(2, g || this.sceneTex);
    this.draw(this.progComp, null, {
      uScene: 0, uBloom: 1, uGrain: 2, uTime: time, uFrame: Math.floor(time * 24),
      uRes: [this.w, this.h], uWeave: [Math.sin(time * 1.7) * .35 + (hash(Math.floor(time * 24)) - .5) * .5, Math.cos(time * 1.3) * .5],
      uFlash: mood.flash || 0, uGrainAmt: mood.grain == null ? .055 : mood.grain,
      uBloomAmt: mood.bloom == null ? .38 : mood.bloom, uVignette: mood.vignette == null ? 1 : mood.vignette,
      uWarm: mood.warm == null ? .5 : mood.warm, uSat: mood.sat == null ? .88 : mood.sat,
      uCA: mood.ca == null ? 1 : mood.ca, uFade: mood.fade == null ? 1 : mood.fade
    });
  }
}
const VS = `#version 300 es
in vec2 p; out vec2 vUv;
void main(){ vUv = p*.5+.5; gl_Position=vec4(p,0.,1.); }`;
const FS_BRIGHT = `#version 300 es
precision highp float; in vec2 vUv; out vec4 o; uniform sampler2D uScene; uniform vec2 uTexel; uniform float uThreshold;
void main(){
  vec3 c = texture(uScene, vUv).rgb;
  float l = dot(c, vec3(.2126,.7152,.0722));
  float k = smoothstep(uThreshold, uThreshold+.35, l);
  o = vec4(c*k, 1.);
}`;
const FS_BLUR = `#version 300 es
precision highp float; in vec2 vUv; out vec4 o; uniform sampler2D uScene; uniform vec2 uTexel; uniform vec2 uDir; uniform float uRadius;
void main(){
  vec2 d = uDir * uTexel * uRadius;
  vec3 c = texture(uScene, vUv).rgb * .227027;
  c += (texture(uScene, vUv+d*1.3846).rgb + texture(uScene, vUv-d*1.3846).rgb) * .316216;
  c += (texture(uScene, vUv+d*3.2308).rgb + texture(uScene, vUv-d*3.2308).rgb) * .070270;
  o = vec4(c,1.);
}`;
const FS_COMP = `#version 300 es
precision highp float; in vec2 vUv; out vec4 o;
uniform sampler2D uScene, uBloom, uGrain;
uniform vec2 uRes, uWeave;
uniform float uTime, uFrame, uFlash, uGrainAmt, uBloomAmt, uVignette, uWarm, uSat, uCA, uFade;
float h(vec2 p){ return fract(sin(dot(p, vec2(12.9898,78.233)))*43758.5453); }
vec3 grade(vec3 c){
  float l = dot(c, vec3(.2126,.7152,.0722));
  c = mix(vec3(l), c, uSat);
  c += vec3(.012,.020,.022) * (1.-l);
  c = pow(max(c,0.), vec3(1.02));
  c = mix(c, vec3(1.) - exp(-c*1.35), .35);
  vec3 hi = vec3(1.02,.94,.80), lo = vec3(.86,.96,1.02);
  c *= mix(lo, hi, smoothstep(.15,.85,l)) * mix(1., 1.06, uWarm);
  return c;
}
void main(){
  vec2 uv = vUv + uWeave / uRes;
  vec2 q = uv - .5;
  float r2 = dot(q,q);
  uv = .5 + q * (1. + .055*r2);
  vec2 ab = q * r2 * .0045 * uCA;
  vec3 c;
  c.r = texture(uScene, uv + ab).r;
  c.g = texture(uScene, uv).g;
  c.b = texture(uScene, uv - ab).b;
  vec3 bloom = texture(uBloom, uv).rgb;
  c += bloom * uBloomAmt * vec3(1.0,.86,.68);
  c = grade(c);
  float vig = smoothstep(1.25,.35,length(q*vec2(1.02,.94)));
  c *= mix(1., vig, .42*uVignette);
  vec3 gr = texture(uGrain, vUv + vec2(fract(uFrame*.137), fract(uFrame*.071))).rgb;
  float g = (gr.r-0.5);
  c += g * uGrainAmt * (1.15 - .4*dot(c,vec3(.33)));
  c += (h(vUv*uRes + uFrame)-.5) * .012;
  c = mix(c, vec3(1.0,.98,.93), uFlash);
  c *= uFade;
  o = vec4(c,1.);
}`;
