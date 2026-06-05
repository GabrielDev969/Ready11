# Integração com Django + Tailwind CSS 3

Guia passo a passo para usar o **GSS Monitoring Design System** no seu projeto Django.
Tudo aqui assume Tailwind 3 via `django-tailwind` **ou** via build manual com Node.

---

## 1. Arquivos que você vai usar

| Arquivo | O que é | Para onde vai |
|---|---|---|
| `tokens.css` | Variáveis CSS (fonte da verdade) | `static/css/` (opcional, p/ uso fora do Tailwind) |
| `tailwind.config.js` | Todos os tokens como tema Tailwind | mescle no seu `tailwind.config.js` |
| `gss-components.css` | Classes `.gss-*` em `@layer components` | importe no seu CSS de entrada |

---

## 2. Instalação (django-tailwind)

```bash
pip install django-tailwind
python manage.py tailwind init   # cria o app "theme"
```

No `settings.py`:
```python
INSTALLED_APPS += ["tailwind", "theme"]
TAILWIND_APP_NAME = "theme"
```

### 2.1 Fundir o tema
Abra `theme/static_src/tailwind.config.js` e copie o conteúdo de
`design-system/tailwind.config.js` para dentro de `theme.extend`.
Confirme que o `content` aponta para as suas templates:

```js
content: [
  '../templates/**/*.html',
  '../../templates/**/*.html',
  '../../**/templates/**/*.html',
],
```

### 2.2 Importar a camada de componentes
No `theme/static_src/src/styles.css` (arquivo de entrada do Tailwind):

```css
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

@tailwind base;
@tailwind components;
@tailwind utilities;

/* cole aqui o conteúdo de gss-components.css, OU: */
@import "../../../design-system/gss-components.css";
```

### 2.3 Rodar
```bash
python manage.py tailwind start    # dev (watch)
python manage.py tailwind build    # produção
```

---

## 3. Fontes

O sistema usa **IBM Plex Sans** (interface) e **IBM Plex Mono** (dados/números).
Ambas estão no Google Fonts (link acima). Para servir localmente (offline / LGPD),
baixe em https://fonts.google.com e coloque em `static/fonts/`, então use `@font-face`.

> ⚠️ **Substituição sinalizada:** se você já tem uma fonte de marca diferente,
> troque `fontFamily.sans`/`fontFamily.mono` no config. A estética técnica depende
> de uma **mono para números** — mantenha alguma monospace nos dados.

---

## 4. Uso nas templates

### Pill de status (o padrão mais comum)
```html
<span class="gss-pill gss-pill-{{ athlete.wellness_status|lower }}">
  <span class="gss-dot" style="background: currentColor"></span>
  {{ athlete.wellness_status }}
</span>
```

Mapeamento de classe por enum:
`EXCELLENT→gss-pill-excellent` · `GOOD→gss-pill-good` ·
`WARNING→gss-pill-warning` · `CRITICAL→gss-pill-critical` ·
`HYDRATED→gss-pill-hydrated` · `ATTENTION→gss-pill-attention` ·
`DEHYDRATED→gss-pill-dehydrated`.

> Dica: crie um **template filter** `status_pill_class` para converter o enum na classe,
> evitando lógica na template.

### KPI card
```html
<div class="gss-kpi">
  <p class="gss-eyebrow">Wellness médio</p>
  <p class="gss-metric-xl">{{ avg_wellness|floatformat:1 }}</p>
</div>
```

### Botão
```html
<button type="submit" class="gss-btn gss-btn-primary">Salvar check-in</button>
```

### Input (Django form)
Adicione a classe no widget:
```python
class CheckinForm(forms.ModelForm):
    sleep_hours = forms.DecimalField(
        widget=forms.NumberInput(attrs={"class": "gss-input"})
    )
```
Ou globalmente com `django-widget-tweaks`:
```html
{% load widget_tweaks %}
{% render_field form.sleep_hours class="gss-input" %}
```

---

## 5. Dashboard condicional por Role

O blueprint pede dashboards diferentes por perfil. Em Django isso é feito na view:

```python
def dashboard(request):
    role = request.user.role
    template = {
        "coach": "dashboard/technical.html",
        "physical_trainer": "dashboard/technical.html",
        "admin": "dashboard/technical.html",
        "nutritionist": "dashboard/nutrition.html",
        "athlete": "dashboard/athlete.html",
    }.get(role, "dashboard/technical.html")
    return render(request, template, get_context_for(role))
```

Os 3 layouts (técnico / nutrição / atleta) estão prototipados no arquivo HTML
raiz do projeto (`index.html`) — use-os como referência de marcação.

---

## 6. oklch() e suporte de navegador

As cores semânticas usam `oklch()`, suportado por todos os navegadores desde 2023.
Se precisar suportar navegadores muito antigos, rode um PostCSS plugin
(`@csstools/postcss-oklab-function`) que gera fallback em rgb automaticamente — já
faz parte do pipeline do Tailwind se você adicionar ao `postcss.config.js`.
