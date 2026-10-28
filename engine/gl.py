"""ModernGL (llvmpipe/EGL) backend: cinematic post-processing and a small 3D mesh renderer."""
import functools
import math
import numpy as np
import moderngl
from .core import W, H

_CTX = None


def ctx():
    global _CTX
    if _CTX is None:
        _CTX = moderngl.create_standalone_context(backend="egl", require=330)
    return _CTX


QUAD_VS = """#version 330
in vec2 p; out vec2 uv;
void main(){ uv = p*0.5+0.5; gl_Position = vec4(p,0.,1.); }"""


@functools.lru_cache(maxsize=None)
def _quad():
    c = ctx()
    return c.buffer(np.array([-1, -1, 1, -1, -1, 1, 1, 1], "f4").tobytes())


def _prog(fs, vs=QUAD_VS):
    return ctx().program(vertex_shader=vs, fragment_shader=fs)


def _qvao(prog):
    return ctx().vertex_array(prog, [(_quad(), "2f", "p")])


# --------------------------------------------------------------------------------------
# Post-processing
# --------------------------------------------------------------------------------------
_DOWN_FS = """#version 330
in vec2 uv; out vec4 o; uniform sampler2D src; uniform vec2 texel; uniform float thresh; uniform int first;
vec3 pre(vec3 c){ if(first==0) return c; float l=max(c.r,max(c.g,c.b)); float k=thresh*0.5;
  float s=clamp(l-thresh+k,0.,2.*k); s=s*s/(4.*k+1e-5); float w=max(s,l-thresh)/max(l,1e-5); return c*w; }
void main(){
  vec2 t=texel;
  vec3 a=texture(src,uv+t*vec2(-2,-2)).rgb, b=texture(src,uv+t*vec2(0,-2)).rgb, c=texture(src,uv+t*vec2(2,-2)).rgb;
  vec3 d=texture(src,uv+t*vec2(-1,-1)).rgb, e=texture(src,uv+t*vec2(1,-1)).rgb;
  vec3 f=texture(src,uv+t*vec2(-2,0)).rgb, g=texture(src,uv).rgb, h=texture(src,uv+t*vec2(2,0)).rgb;
  vec3 i=texture(src,uv+t*vec2(-1,1)).rgb, j=texture(src,uv+t*vec2(1,1)).rgb;
  vec3 k=texture(src,uv+t*vec2(-2,2)).rgb, l=texture(src,uv+t*vec2(0,2)).rgb, m=texture(src,uv+t*vec2(2,2)).rgb;
  vec3 r=(d+e+i+j)*0.125 + (a+c+k+m)*0.03125 + (b+f+h+l)*0.0625 + g*0.125;
  o=vec4(pre(r),1.);
}"""

_UP_FS = """#version 330
in vec2 uv; out vec4 o; uniform sampler2D src; uniform sampler2D base; uniform vec2 texel; uniform float radius;
void main(){
  vec2 t=texel*radius;
  vec3 s=texture(src,uv+vec2(-t.x,-t.y)).rgb + 2.*texture(src,uv+vec2(0,-t.y)).rgb + texture(src,uv+vec2(t.x,-t.y)).rgb
       + 2.*texture(src,uv+vec2(-t.x,0)).rgb + 4.*texture(src,uv).rgb + 2.*texture(src,uv+vec2(t.x,0)).rgb
       + texture(src,uv+vec2(-t.x,t.y)).rgb + 2.*texture(src,uv+vec2(0,t.y)).rgb + texture(src,uv+vec2(t.x,t.y)).rgb;
  o=vec4(texture(base,uv).rgb + s/16., 1.);
}"""

_FINAL_FS = """#version 330
in vec2 uv; out vec4 o;
uniform sampler2D src; uniform sampler2D bloom; uniform sampler2D bloomWide;
uniform float bloomAmt, halation, ca, vignette, grain, exposure, time, contrast, sat, flash, distort;
uniform vec3 lift, gain, gammaV, flashCol;
uniform vec2 res;
float h12(vec2 p){ vec3 p3=fract(vec3(p.xyx)*.1031); p3+=dot(p3,p3.yzx+33.33); return fract((p3.x+p3.y)*p3.z); }
vec3 filmic(vec3 x){ // display-referred: linear below 0.75, smooth shoulder above (bloom rolls off)
  x=max(x,0.); vec3 k=vec3(0.75); vec3 over=max(x-k,0.);
  return min(x,k) + 0.25*(1.-exp(-over/0.25)); }
void main(){
  vec2 c=uv-0.5; float r2=dot(c*vec2(res.x/res.y,1.),c*vec2(res.x/res.y,1.));
  vec2 uvd = uv + c*r2*distort;
  vec2 dir = c*ca;
  vec3 col;
  col.r=texture(src,uvd+dir).r; col.g=texture(src,uvd).g; col.b=texture(src,uvd-dir).b;
  vec3 b = texture(bloom,uvd).rgb; vec3 bw = texture(bloomWide,uvd).rgb;
  col += b*bloomAmt + bw*bloomAmt*0.6;
  col += bw*vec3(1.0,0.32,0.18)*halation;           // film halation: warm red fringe around highlights
  col *= exposure;
  col = mix(col, flashCol, flash);
  col = filmic(col);
  // grade: lift / gamma / gain (ASC-CDL-ish)
  col = col*gain + lift*(1.-col);
  col = pow(max(col,0.), 1./gammaV);
  float l=dot(col,vec3(0.2126,0.7152,0.0722));
  col = mix(vec3(l), col, sat);
  col = (col-0.5)*contrast+0.5;
  // vignette (elliptical, soft)
  float v = smoothstep(0.95, 0.15, length(c*vec2(1.0, 0.78))*1.25);
  col *= mix(1.0, v, vignette);
  // luma-weighted film grain, 2-frame decorrelated
  vec2 px = uv*res;
  float g1 = h12(floor(px/1.6)+fract(time*13.17)*311.) - 0.5;
  float g2 = h12(floor(px/1.0)+fract(time*7.31)*173.) - 0.5;
  float gl = mix(g1,g2,0.45);
  float lw = 1.0 - abs(l-0.45)*1.2;
  col += gl*grain*(0.55+0.45*lw);
  // triangular dither against banding in 8-bit
  col += (h12(px+fract(time)*97.)+h12(px*1.37+11.)-1.)/255.;
  o=vec4(clamp(col,0.,1.),1.);
}"""


class Post:
    def __init__(self, w=W, h=H, levels=6):
        c = ctx()
        self.w, self.h = w, h
        self.src = c.texture((w, h), 4, dtype="f2")
        self.src.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self.src.repeat_x = self.src.repeat_y = False
        self.down_p = _prog(_DOWN_FS)
        self.up_p = _prog(_UP_FS)
        self.fin_p = _prog(_FINAL_FS)
        self.down_v = _qvao(self.down_p)
        self.up_v = _qvao(self.up_p)
        self.fin_v = _qvao(self.fin_p)
        self.mips, self.ups = [], []
        ww, hh = w, h
        for i in range(levels):
            ww, hh = max(ww // 2, 1), max(hh // 2, 1)
            t = c.texture((ww, hh), 4, dtype="f2")
            t.filter = (moderngl.LINEAR, moderngl.LINEAR)
            t.repeat_x = t.repeat_y = False
            u = c.texture((ww, hh), 4, dtype="f2")
            u.filter = (moderngl.LINEAR, moderngl.LINEAR)
            u.repeat_x = u.repeat_y = False
            self.mips.append((t, c.framebuffer([t])))
            self.ups.append((u, c.framebuffer([u])))
        self.out = c.texture((w, h), 4)
        self.out_fb = c.framebuffer([self.out])

    def run(self, rgb, p, t):
        """rgb: HxWx3/4 float32 linear-ish image (top row first). p: dict of params."""
        c = ctx()
        if rgb.shape[2] == 3:
            rgb = np.concatenate([rgb, np.ones(rgb.shape[:2] + (1,), np.float32)], -1)
        self.src.write(np.ascontiguousarray(rgb[::-1]).astype("f2").tobytes())
        # downsample chain
        prev = self.src
        pw, ph = self.w, self.h
        for i, (tex, fb) in enumerate(self.mips):
            fb.use()
            prev.use(0)
            self.down_p["src"] = 0
            self.down_p["texel"] = (1.0 / pw, 1.0 / ph)
            self.down_p["thresh"] = p.get("bloom_thresh", 0.75)
            self.down_p["first"] = 1 if i == 0 else 0
            self.down_v.render(moderngl.TRIANGLE_STRIP)
            prev = tex
            pw, ph = tex.size
        # upsample (tent) accumulate
        n = len(self.mips)
        cur = self.mips[-1][0]
        for i in range(n - 2, -1, -1):
            tex, fb = self.ups[i]
            fb.use()
            cur.use(0)
            self.mips[i][0].use(1)
            self.up_p["src"] = 0
            self.up_p["base"] = 1
            sw, sh = cur.size
            self.up_p["texel"] = (1.0 / sw, 1.0 / sh)
            self.up_p["radius"] = 1.0
            self.up_v.render(moderngl.TRIANGLE_STRIP)
            cur = tex
        bloom_t = self.ups[0][0]
        wide_t = self.ups[2][0]
        self.out_fb.use()
        self.src.use(0)
        bloom_t.use(1)
        wide_t.use(2)
        fp = self.fin_p
        fp["src"], fp["bloom"], fp["bloomWide"] = 0, 1, 2
        fp["bloomAmt"] = p.get("bloom", 0.25)
        fp["halation"] = p.get("halation", 0.06)
        fp["ca"] = p.get("ca", 0.0018)
        fp["vignette"] = p.get("vignette", 0.55)
        fp["grain"] = p.get("grain", 0.045)
        fp["exposure"] = p.get("exposure", 1.0)
        fp["time"] = t
        fp["contrast"] = p.get("contrast", 1.04)
        fp["sat"] = p.get("sat", 0.96)
        fp["flash"] = p.get("flash", 0.0)
        fp["flashCol"] = p.get("flash_col", (1.0, 0.95, 0.88))
        fp["distort"] = p.get("distort", 0.02)
        fp["lift"] = p.get("lift", (0.012, 0.014, 0.02))
        fp["gain"] = p.get("gain", (1.0, 0.99, 0.97))
        fp["gammaV"] = p.get("gamma", (1.0, 1.0, 1.0))
        fp["res"] = (float(self.w), float(self.h))
        self.fin_v.render(moderngl.TRIANGLE_STRIP)
        data = self.out_fb.read(components=3, alignment=1)
        img = np.frombuffer(data, np.uint8).reshape(self.h, self.w, 3)[::-1]
        return img


# --------------------------------------------------------------------------------------
# 3D
# --------------------------------------------------------------------------------------
def perspective(fovy_deg, aspect, near, far):
    f = 1.0 / math.tan(math.radians(fovy_deg) / 2)
    m = np.zeros((4, 4), np.float32)
    m[0, 0] = f / aspect
    m[1, 1] = f
    m[2, 2] = (far + near) / (near - far)
    m[2, 3] = 2 * far * near / (near - far)
    m[3, 2] = -1
    return m


def look_at(eye, target, up=(0, 0, 1)):
    eye, target, up = (np.asarray(v, np.float32) for v in (eye, target, up))
    f = target - eye
    f /= np.linalg.norm(f)
    s = np.cross(f, up)
    s /= np.linalg.norm(s) + 1e-9
    u = np.cross(s, f)
    m = np.eye(4, dtype=np.float32)
    m[0, :3], m[1, :3], m[2, :3] = s, u, -f
    m[0, 3], m[1, 3], m[2, 3] = -s @ eye, -u @ eye, f @ eye
    return m


def project(points, mvp, w=W, h=H):
    """Project Nx3 world points to pixel coords (x right, y down). Returns Nx2 and depth/visibility."""
    p = np.asarray(points, np.float32)
    ph = np.concatenate([p, np.ones((len(p), 1), np.float32)], 1) @ mvp.T
    wv = ph[:, 3:4]
    ndc = ph[:, :3] / np.where(np.abs(wv) < 1e-6, 1e-6, wv)
    xs = (ndc[:, 0] * 0.5 + 0.5) * w
    ys = (1 - (ndc[:, 1] * 0.5 + 0.5)) * h
    return np.stack([xs, ys], 1), ndc[:, 2], wv[:, 0] > 0


MESH_VS = """#version 330
uniform mat4 mvp; uniform mat4 model;
in vec3 pos; in vec3 nrm; in vec4 col;
out vec3 wpos; out vec3 wn; out vec4 vcol;
void main(){ vec4 w = model*vec4(pos,1.); wpos=w.xyz; wn=normalize(mat3(model)*nrm); vcol=col; gl_Position=mvp*vec4(pos,1.); }"""

LIT_FS = """#version 330
in vec3 wpos; in vec3 wn; in vec4 vcol; out vec4 o;
uniform vec3 eye, ldir, lcol, skyc, groundc, fogc, rimc; uniform float fogNear, fogFar, alpha, spec, shin, rim;
void main(){
  vec3 n=normalize(wn); if(!gl_FrontFacing) n=-n;
  vec3 v=normalize(eye-wpos); vec3 l=normalize(ldir);
  float nd=max(dot(n,l),0.);
  float wrap=max((dot(n,l)+0.35)/1.35,0.);
  vec3 amb=mix(groundc,skyc,n.z*0.5+0.5);
  vec3 h=normalize(l+v); float s=pow(max(dot(n,h),0.),shin)*spec;
  float fr=pow(1.-max(dot(n,v),0.),3.)*rim;
  vec3 c=vcol.rgb*(amb+lcol*(0.35*nd+0.65*wrap)) + lcol*s + rimc*fr;
  float d=length(eye-wpos); float f=smoothstep(fogNear,fogFar,d);
  c=mix(c,fogc,f);
  o=vec4(c*alpha*vcol.a, alpha*vcol.a);
}"""

CITY_FS = """#version 330
in vec3 wpos; in vec3 wn; in vec4 vcol; out vec4 o;
uniform vec3 eye, ldir, lcol, skyc, fogc, winc; uniform float fogNear, fogFar, alpha, winAmt, time, glow;
uniform vec2 hl; uniform float hlR, hlAmt, wscale; uniform vec3 hlc;
float h12(vec2 p){ vec3 p3=fract(vec3(p.xyx)*.1031); p3+=dot(p3,p3.yzx+33.33); return fract((p3.x+p3.y)*p3.z); }
void main(){
  vec3 n=normalize(wn);
  vec3 base=vcol.rgb;
  float roof = step(0.7, n.z);
  float nd = max(dot(n, normalize(ldir)), 0.);
  vec3 c = base*(skyc*(0.55+0.45*n.z) + lcol*nd*0.6);
  if(roof<0.5){
    // procedural windows on facades
    vec3 wp = wpos*wscale;   // metres
    vec2 fuv = vec2(dot(wp.xy, normalize(vec2(-n.y,n.x)))/3.2, wp.z/3.4);
    vec2 cell=floor(fuv); vec2 f=fract(fuv);
    float win = step(0.22,f.x)*step(f.x,0.78)*step(0.25,f.y)*step(f.y,0.75)*step(1.0,wp.z);
    float on = step(0.62, h12(cell + vcol.a*91.7));
    float warm = h12(cell*1.7+3.1);
    vec3 wc = mix(winc, vec3(1.0,0.86,0.62), warm*0.5);
    c += win*on*wc*winAmt*(0.6+0.4*h12(cell+7.));
    c *= 0.85 + 0.15*smoothstep(0.,30.,wp.z);
  } else {
    c = base*(skyc*0.9 + lcol*0.35);
  }
  // highlight disc (a target building glows)
  float dh = length(wpos.xy-hl);
  float hm = smoothstep(hlR,0.,dh);
  c = mix(c, c*hlc*2.2 + hlc*0.08, hm*clamp(hlAmt,0.,1.));      // tint the target building
  c += hlc*hlAmt*0.35*hm*roof;
  float d=length(eye-wpos); float fo=smoothstep(fogNear,fogFar,d);
  c=mix(c,fogc,fo);
  o=vec4(c*alpha, alpha);
}"""

TEX_VS = """#version 330
uniform mat4 mvp; in vec3 pos; in vec2 tc; out vec2 uv; out vec3 wpos;
void main(){ uv=tc; wpos=pos; gl_Position=mvp*vec4(pos,1.); }"""

TEX_FS = """#version 330
in vec2 uv; in vec3 wpos; out vec4 o; uniform sampler2D tex; uniform vec3 eye, fogc; uniform float fogNear, fogFar, alpha;
void main(){ vec4 c=texture(tex,uv); float d=length(eye-wpos); float f=smoothstep(fogNear,fogFar,d);
  c.rgb=mix(c.rgb, fogc*c.a, f); o=c*alpha; }"""


class Mesh:
    def __init__(self, pos, nrm, col, idx=None):
        c = ctx()
        self.n = len(pos)
        data = np.concatenate([np.asarray(pos, "f4"), np.asarray(nrm, "f4"), np.asarray(col, "f4")], 1)
        self.vbo = c.buffer(data.astype("f4").tobytes())
        self.ibo = c.buffer(np.asarray(idx, "i4").tobytes()) if idx is not None else None
        self.vaos = {}

    def vao(self, prog):
        k = id(prog)
        if k not in self.vaos:
            self.vaos[k] = ctx().vertex_array(prog, [(self.vbo, "3f 3f 4f", "pos", "nrm", "col")],
                                              index_buffer=self.ibo)
        return self.vaos[k]


class TexPlane:
    def __init__(self, corners, image_rgba, mipmap=True):
        """corners: 4x3 world positions (tl, tr, bl, br). image: HxWx4 uint8 straight alpha."""
        c = ctx()
        img = np.ascontiguousarray(image_rgba[::-1])
        a = img[..., 3:4].astype(np.float32) / 255.0
        pm = (img[..., :3].astype(np.float32) * a).astype(np.uint8)
        img = np.concatenate([pm, img[..., 3:4]], -1)
        self.tex = c.texture((img.shape[1], img.shape[0]), 4, img.tobytes())
        if mipmap:
            self.tex.build_mipmaps()
            self.tex.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR)
            self.tex.anisotropy = 16.0
        tl, tr, bl, br = [np.asarray(x, "f4") for x in corners]
        data = np.array([[*bl, 0, 0], [*br, 1, 0], [*tl, 0, 1], [*tr, 1, 1]], "f4")
        self.vbo = c.buffer(data.tobytes())
        self.vaos = {}

    def vao(self, prog):
        k = id(prog)
        if k not in self.vaos:
            self.vaos[k] = ctx().vertex_array(prog, [(self.vbo, "3f 2f", "pos", "tc")])
        return self.vaos[k]


class Renderer3D:
    """Offscreen MSAA renderer returning premultiplied RGBA float32 images (top row first)."""

    def __init__(self, w=W, h=H, samples=4):
        c = ctx()
        self.w, self.h = w, h
        self.ms_col = c.renderbuffer((w, h), 4, samples=samples, dtype="f2")
        self.ms_dep = c.depth_renderbuffer((w, h), samples=samples)
        self.ms_fb = c.framebuffer([self.ms_col], self.ms_dep)
        self.res_tex = c.texture((w, h), 4, dtype="f2")
        self.res_fb = c.framebuffer([self.res_tex])
        self.lit = _prog(LIT_FS, MESH_VS)
        self.city = _prog(CITY_FS, MESH_VS)
        self.texp = _prog(TEX_FS, TEX_VS)

    def begin(self, clear=(0, 0, 0, 0)):
        c = ctx()
        self.ms_fb.use()
        c.viewport = (0, 0, self.w, self.h)
        c.clear(*clear, depth=1.0)
        c.enable(moderngl.DEPTH_TEST)
        c.blend_func = moderngl.ONE, moderngl.ONE_MINUS_SRC_ALPHA
        c.enable(moderngl.BLEND)

    @staticmethod
    def _set(prog, **u):
        for k, v in u.items():
            if k in prog:
                if isinstance(v, np.ndarray) and v.shape == (4, 4):
                    prog[k].write(v.T.astype("f4").tobytes())
                else:
                    prog[k].value = v

    def draw_mesh(self, mesh, mvp, model=None, material="lit", depth_write=True, **u):
        c = ctx()
        prog = self.lit if material == "lit" else self.city
        model = np.eye(4, dtype=np.float32) if model is None else model
        defaults = dict(ldir=(0.4, -0.5, 0.8), lcol=(1, 1, 1), skyc=(0.35, 0.38, 0.42), groundc=(0.1, 0.1, 0.1),
                        fogc=(0, 0, 0), rimc=(0.6, 0.7, 0.8), fogNear=1e6, fogFar=2e6, alpha=1.0, spec=0.2,
                        shin=24.0, rim=0.0, winc=(1.0, 0.78, 0.45), winAmt=1.0, time=0.0, glow=0.0,
                        hl=(0.0, 0.0), hlR=1.0, hlAmt=0.0, hlc=(1.0, 0.5, 0.3), eye=(0, 0, 10), wscale=1.0)
        defaults.update(u)
        self._set(prog, mvp=mvp, model=model, **defaults)
        c.depth_mask = depth_write
        mesh.vao(prog).render(moderngl.TRIANGLES)
        c.depth_mask = True

    def draw_plane(self, plane, mvp, eye=(0, 0, 10), fogc=(0, 0, 0), fogNear=1e6, fogFar=2e6, alpha=1.0,
                   depth_write=True):
        c = ctx()
        plane.tex.use(0)
        self._set(self.texp, mvp=mvp, eye=eye, fogc=fogc, fogNear=fogNear, fogFar=fogFar, alpha=alpha)
        self.texp["tex"] = 0
        c.depth_mask = depth_write
        plane.vao(self.texp).render(moderngl.TRIANGLE_STRIP)
        c.depth_mask = True

    def end(self):
        c = ctx()
        c.copy_framebuffer(self.res_fb, self.ms_fb)
        c.disable(moderngl.DEPTH_TEST)
        data = self.res_fb.read(components=4, dtype="f2", alignment=1)
        img = np.frombuffer(data, np.float16).reshape(self.h, self.w, 4)[::-1].astype(np.float32)
        return img


# --------------------------------------------------------------------------------------
# Geometry builders
# --------------------------------------------------------------------------------------
def lathe(profile, segments=96, color=(0.8, 0.8, 0.8, 1.0), z_up=True):
    """Revolve a 2D profile [(radius, height), ...] around the Z axis. Returns pos, nrm, col arrays."""
    prof = np.asarray(profile, np.float32)
    # profile normals from tangent
    tang = np.gradient(prof, axis=0)
    pn = np.stack([tang[:, 1], -tang[:, 0]], 1)
    pn /= np.linalg.norm(pn, axis=1, keepdims=True) + 1e-9
    angs = np.linspace(0, 2 * np.pi, segments + 1)
    P, N = [], []
    for i in range(len(prof) - 1):
        for j in range(segments):
            a0, a1 = angs[j], angs[j + 1]
            quad = []
            for (k, a) in ((i, a0), (i, a1), (i + 1, a1), (i + 1, a0)):
                r, zz = prof[k]
                quad.append(((r * math.cos(a), r * math.sin(a), zz),
                             (pn[k, 0] * math.cos(a), pn[k, 0] * math.sin(a), pn[k, 1])))
            for t in (0, 1, 2, 0, 2, 3):
                P.append(quad[t][0])
                N.append(quad[t][1])
    P = np.asarray(P, np.float32)
    N = np.asarray(N, np.float32)
    C = np.tile(np.asarray(color, np.float32), (len(P), 1))
    return P, N, C


def box(cx, cy, cz, sx, sy, sz, color):
    x0, x1 = cx - sx / 2, cx + sx / 2
    y0, y1 = cy - sy / 2, cy + sy / 2
    z0, z1 = cz, cz + sz
    faces = [
        ((x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1), (0, 0, 1)),
        ((x0, y0, z0), (x0, y1, z0), (x1, y1, z0), (x1, y0, z0), (0, 0, -1)),
        ((x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1), (0, -1, 0)),
        ((x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1), (0, 1, 0)),
        ((x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (-1, 0, 0)),
        ((x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1), (1, 0, 0)),
    ]
    P, N = [], []
    for a, b, c, d, n in faces:
        for v in (a, b, c, a, c, d):
            P.append(v)
            N.append(n)
    P = np.asarray(P, np.float32)
    return P, np.asarray(N, np.float32), np.tile(np.asarray(color, np.float32), (len(P), 1))


def merge(*parts):
    return tuple(np.concatenate([p[i] for p in parts], 0) for i in range(3))
