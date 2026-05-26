# Entrega 3 - Explicacao do Codigo

Esta entrega adiciona iluminacao local ao ray-casting. Antes, o programa apenas encontrava o objeto atingido pelo raio e retornava sua cor. Agora, depois de encontrar a intersecao mais proxima, o codigo calcula a cor usando o modelo de Phong sem recursao e tambem testa sombras.

Os trechos abaixo mostram as partes principais do codigo da entrega 3 e explicam por que cada uma foi usada.

## 1. Fluxo Principal do Render

O fluxo principal fica em `main.py`, dentro de `renderizar`.

```python
raio = gerar_raio(i, j, C, u, v, w, largura, altura, d)
obj_atingido, t = encontrar_intersecao(raio, objetos)

if obj_atingido:
    ponto = raio.ponto_em(t)
    normal = normal_orientada(obj_atingido, ponto, raio)
    cor = iluminar_phong(obj_atingido, ponto, normal, raio, scene, objetos)
    r = int(cor.x * 255)
    g = int(cor.y * 255)
    b = int(cor.z * 255)
else:
    r = g = b = 0
```

Esse trecho substitui o comportamento antigo, que retornava apenas a cor do material. Agora o codigo precisa guardar o objeto atingido e a distancia `t`, porque o modelo de Phong precisa calcular o ponto exato da intersecao, a normal naquele ponto, a direcao da luz e a direcao da camera.

Se nenhum objeto for atingido, o pixel continua preto. Se houver intersecao, o programa calcula a iluminacao antes de escrever a cor no `.ppm`.

## 2. Intersecao Mais Proxima

A funcao `encontrar_intersecao` procura o menor `t` positivo entre todos os objetos.

```python
def encontrar_intersecao(raio, objetos):
    t_min, obj_atingido = float("inf"), None
    for obj in objetos:
        t = obj.intersectar(raio)
        if t is not None and t < t_min:
            t_min, obj_atingido = t, obj
    if obj_atingido is None:
        return None, None
    return obj_atingido, t_min
```

Isso e importante porque um raio pode interceptar mais de um objeto, mas so o mais proximo da camera deve aparecer no pixel. Separar essa etapa tambem deixa claro que primeiro o ray-casting descobre a superficie visivel e depois o Phong calcula a cor dessa superficie.

## 3. Materiais e Coeficientes

O modelo de Phong usa varios coeficientes do material: `kd`, `ka`, `ks` e `ns`. No projeto, a cor difusa tambem pode vir como `color`, entao o codigo converte esses campos para `Vetor`.

```python
def material_para_vetor(material, atributo, padrao=None):
    valor = getattr(material, atributo, None)
    if valor is None:
        return padrao if padrao is not None else Vetor(0.0, 0.0, 0.0)
    return cor_para_vetor(valor)

def coeficiente_difuso(obj):
    if hasattr(obj, "O_d"):
        return obj.O_d
    return material_para_vetor(obj.material, "color")
```

`material_para_vetor` evita repetir conversoes de cor em varios pontos do codigo. `coeficiente_difuso` existe porque malhas podem ter uma cor difusa `O_d` vinda do material da propria malha, enquanto esferas e planos usam `obj.material.color`.

No parser, `kd` foi aceito como alias de `color`:

```python
if "color" in node:
    m.color = SceneJsonLoader._parse_color(node["color"], f"{m.name}.color")
if "kd" in node:
    m.color = SceneJsonLoader._parse_color(node["kd"], f"{m.name}.kd")
```

Isso foi feito porque o enunciado chama a cor difusa de `kd`, mas cenas antigas do projeto ja usavam `color`. Assim, os dois formatos funcionam.

## 4. Modelo de Phong

A funcao principal da entrega 3 e `iluminar_phong`.

```python
def iluminar_phong(obj, ponto, normal, raio, scene, objetos):
    material = obj.material
    ia = cor_para_vetor(scene.global_light.color)
    ka = material_para_vetor(material, "ka")
    kd = coeficiente_difuso(obj)
    ks = material_para_vetor(material, "ks")
    eta = max(float(getattr(material, "ns", 1.0)), 1.0)

    cor = multiplicar_componentes(ka, ia)
    observador = (raio.origem - ponto).normalizar()
```

Aqui o codigo separa os coeficientes do material e inicia a cor com a luz ambiente:

```text
ka * Ia
```

O `observador` e o vetor `V` da equacao de Phong. Ele aponta do ponto de intersecao para a camera, porque os raios primarios saem da camera.

Depois vem o loop das luzes pontuais:

```python
for luz in scene.light_list:
    vetor_luz = luz.pos - ponto
    distancia_luz = vetor_luz.modulo()
    if distancia_luz <= EPSILON_SOMBRA:
        continue

    direcao_luz = vetor_luz / distancia_luz
    n_dot_l = max(0.0, normal.prodEscalar(direcao_luz))
    if n_dot_l <= 0.0:
        continue

    if esta_em_sombra(ponto, normal, direcao_luz, distancia_luz, objetos):
        continue
```

Esse trecho calcula `L`, que e o vetor do ponto ate a luz. O produto `N . L` mede o quanto a superficie esta virada para a luz. Se esse valor for menor ou igual a zero, a luz esta atras da superficie e nao deve contribuir.

O teste de sombra acontece antes de somar a luz. Se algum objeto bloquear o caminho ate a fonte, essa luz e ignorada para aquele ponto.

Quando a luz contribui, o codigo soma os termos difuso e especular:

```python
il = cor_para_vetor(luz.color)
difusa = multiplicar_componentes(il, kd) * n_dot_l

reflexao = (normal * (2.0 * n_dot_l) - direcao_luz).normalizar()
r_dot_v = max(0.0, reflexao.prodEscalar(observador))
especular = multiplicar_componentes(il, ks) * (r_dot_v ** eta)

cor = cor + difusa + especular
```

O termo difuso representa a iluminacao espalhada pela superficie:

```text
Il * kd * max(0, N . L)
```

O termo especular representa o brilho:

```text
Il * ks * max(0, R . V)^eta
```

O vetor `R` e a direcao de reflexao da luz. O vetor `V` aponta para a camera. Quando `R` e `V` ficam bem alinhados, o brilho aumenta. O `eta`, vindo de `ns`, controla se esse brilho fica mais aberto ou mais concentrado.

No final, a cor e limitada:

```python
return limitar_cor(cor)
```

Isso evita valores abaixo de `0` ou acima de `1` antes da conversao para RGB de `0` a `255`.

## 5. Sombras

As sombras foram implementadas em `esta_em_sombra`.

```python
def esta_em_sombra(ponto, normal, direcao_luz, distancia_luz, objetos):
    deslocamento = normal if normal.prodEscalar(direcao_luz) >= 0 else -normal
    origem_sombra = ponto + deslocamento * EPSILON_SOMBRA
    raio_sombra = Raio(origem_sombra, direcao_luz)

    for obj in objetos:
        t = obj.intersectar(raio_sombra)
        if t is not None and EPSILON_SOMBRA < t < distancia_luz - EPSILON_SOMBRA:
            return True
    return False
```

Esse metodo cria um raio secundario que sai do ponto de intersecao em direcao a luz. Se esse raio atinge outro objeto antes de chegar na luz, o ponto esta em sombra para aquela fonte luminosa.

O `EPSILON_SOMBRA` serve para deslocar um pouco a origem do raio. Sem isso, por erro numerico, o raio de sombra poderia bater imediatamente na propria superficie que acabou de ser atingida.

## 6. Normais dos Objetos

Phong depende da normal `N`, entao cada objeto precisa calcular sua normal no ponto atingido.

Na esfera:

```python
def normal_em(self, ponto: Ponto):
    return (ponto - self.centro).normalizar()
```

A normal da esfera e o vetor que sai do centro em direcao ao ponto da superficie. Isso funciona porque todos os pontos da esfera estao a uma distancia constante do centro.

No plano:

```python
def normal_em(self, ponto):
    return self.normal
```

O plano tem uma normal constante, entao nao depende do ponto atingido.

Na malha, a normal depende do triangulo atingido:

```python
def normal_em(self, ponto):
    if self.ultimo_indice_triangulo is None:
        return Vetor(0.0, 1.0, 0.0)

    fallback = self.normais_triangulos[self.ultimo_indice_triangulo]
    normal_obj = self._normal_obj_interpolada(self.ultimo_indice_triangulo, fallback)
    if normal_obj is not None:
        return normal_obj
```

A malha guarda qual triangulo foi atingido durante a intersecao. Se o OBJ tiver normais (`vn`), o codigo usa essas normais interpoladas. Se nao tiver, usa a normal do triangulo como fallback.

Essa parte e necessaria porque malhas sao formadas por varios triangulos, e cada ponto pode ter uma normal diferente dependendo da face atingida.

## 7. Normal Orientada

Antes de iluminar, o codigo orienta a normal em relacao ao raio da camera.

```python
def normal_orientada(obj, ponto, raio):
    normal = obj.normal_em(ponto)
    if normal.modulo() == 0:
        normal = Vetor(0.0, 1.0, 0.0)
    else:
        normal = normal.normalizar()
    if normal.prodEscalar(raio.direcao) > 0:
        normal = -normal
    return normal
```

Isso evita usar uma normal apontando para o lado errado. Em malhas OBJ, a ordem dos vertices pode fazer algumas faces ficarem com a normal invertida. Se isso acontecer, o produto `N . L` pode dar errado e a iluminacao fica escura ou invertida.

## 8. Termos Recursivos Ignorados

A equacao completa tambem possui:

```text
kr * Ir + kt * It
```

Esses termos representam reflexao e refracao. Eles foram deixados de fora porque a entrega 3 pede Phong sem recursao. Para calcular `Ir` e `It`, seria necessario disparar novos raios refletidos e refratados e chamar o ray-casting novamente.

## 9. Arquivos Principais

- `main.py`: contem o fluxo do render, Phong, sombras, busca de intersecao e orientacao da normal.
- `src/Esfera.py`: calcula a normal da esfera.
- `src/Plano.py`: retorna a normal constante do plano.
- `src/Malha.py`: guarda o triangulo atingido e calcula a normal da malha.
- `utils/Scene/sceneParser.py`: le `kd`, `ka`, `ks`, `kr`, `kt` e `ns`.
- `utils/Scene/sceneSchema.py`: define os dados de material e luz usados na cena.

## Resumo

A entrega 3 transforma o ray-casting simples em um renderizador com iluminacao local. O programa ainda nao faz reflexao ou refracao recursiva, mas agora calcula luz ambiente, difusa, especular e sombras. Com isso, os objetos deixam de aparecer apenas com cor plana e passam a ter volume visual, brilho e regioes escurecidas quando a luz e bloqueada.
