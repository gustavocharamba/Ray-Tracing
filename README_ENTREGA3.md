# Entrega 3 - Explicacao do Codigo

Esta entrega adiciona iluminacao local ao ray-casting. Antes, o programa apenas encontrava o objeto atingido pelo raio e retornava sua cor. Agora, depois de encontrar a intersecao mais proxima, o codigo calcula a cor usando o modelo de Phong sem recursao e tambem testa sombras.

Os trechos abaixo mostram as partes principais do codigo da entrega 3 e explicam por que cada uma foi usada.

## 1. Fluxo Principal do Render

O fluxo principal fica em `main.py`, dentro de `renderizar`.

Arquivo e linhas: `main.py:225-237`.

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

Esse trecho e o ponto onde o ray-casting deixa de ser apenas "qual objeto foi atingido?" e passa a responder "como esse ponto deve ser iluminado?". A variavel `t` e a distancia ao longo do raio, isto e, o parametro da equacao:

```text
P = O + t * D
```

`O` e a origem do raio, `D` e sua direcao, e `P` e o ponto real da superficie atingida. Esse ponto e necessario porque Phong nao ilumina o objeto inteiro de uma vez; ele ilumina o ponto visivel naquele pixel. A partir de `P`, o codigo consegue calcular a normal `N`, o vetor ate a luz `L`, o vetor ate a camera `V` e tambem a distancia ate a luz usada no teste de sombra.

Se nenhum objeto for atingido, nao existe superficie para iluminar, entao o pixel fica preto. Se houver intersecao, o programa primeiro descobre o ponto visivel e so depois calcula a cor com Phong.

## 2. Intersecao Mais Proxima

A funcao `encontrar_intersecao` procura o menor `t` positivo entre todos os objetos.

Arquivo e linhas: `main.py:154-162`.

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

Isso e importante porque um raio pode atravessar varios objetos no caminho. Por exemplo, ele pode bater primeiro em um cubo e depois em uma malha atras dele. O pixel deve mostrar apenas o primeiro objeto, porque ele bloqueia os objetos que estao atras. Por isso a funcao guarda o menor `t`: quanto menor o `t`, mais perto da camera esta a intersecao.

Separar essa etapa tambem evita calcular iluminacao para superficies que nao aparecem. O Phong so deve ser executado depois que o codigo ja sabe qual e a superficie realmente visivel naquele pixel.

## 3. Materiais e Coeficientes

O modelo de Phong usa os coeficientes de material pedidos no enunciado. Os coeficientes de cor ficam em `[0, 1]^3`, e o expoente de brilho precisa ser positivo:

- `kd`: coeficiente difuso.
- `ks`: coeficiente especular.
- `ka`: coeficiente ambiental.
- `kr`: coeficiente de reflexao.
- `kt`: coeficiente de transmissao.
- `eta > 0`: coeficiente de rugosidade/brilho. No codigo, ele vem do campo `ns`.

No projeto, a cor difusa tambem pode vir como `color`, entao o codigo converte esses campos para `Vetor`.

Arquivo e linhas: `main.py:133-142`.

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

`material_para_vetor` existe porque os coeficientes do material chegam como estruturas de cor (`r`, `g`, `b`), mas os calculos de Phong usam operacoes vetoriais e multiplicacao componente a componente. Converter esses valores para `Vetor` deixa o calculo de `ka * Ia`, `Il * kd` e `Il * ks` mais direto.

`coeficiente_difuso` centraliza a escolha do `kd`. Esferas e planos usam `obj.material.color`; malhas podem guardar a cor difusa em `O_d`, principalmente quando a cor vem da leitura da malha/material. Assim, o restante do Phong nao precisa saber de onde o `kd` veio, apenas usa o valor ja resolvido.

No parser, `kd` foi aceito como alias de `color`:

Arquivo e linhas: `utils/Scene/sceneParser.py:88-89`.

```python
if "color" in node:
    m.color = SceneJsonLoader._parse_color(node["color"], f"{m.name}.color")
if "kd" in node:
    m.color = SceneJsonLoader._parse_color(node["kd"], f"{m.name}.kd")
```

Isso foi feito porque o enunciado chama a cor difusa de `kd`, mas cenas antigas do projeto ja usavam `color`. Na pratica, os dois nomes representam o mesmo termo da equacao: a cor difusa que multiplica a intensidade da luz no termo `Il * kd * (N . L)`.

## 4. Fontes de Luz

A entrega pede fontes de luz pontuais e luz ambiente. No codigo, isso aparece nos dados da cena:

Arquivo e linhas: `utils/Scene/sceneSchema.py:49-52` e `utils/Scene/sceneSchema.py:83-86`.

```python
class LightData:
    pos: Ponto
    color: ColorData

class SceneData:
    global_light: LightData
    light_list: List[LightData]
```

`global_light` representa a luz ambiente `Ia`. Ela nao tem uma direcao especifica e nao vem de um ponto no espaco; por isso nao precisa de vetor `L`, nao gera brilho especular e nao e bloqueada por sombra. Ela entra uma unica vez no calculo como `ka * Ia`.

`light_list` guarda as luzes pontuais. Cada luz pontual possui:

- `pos`: posicao da luz no espaco;
- `color`: cor/intensidade da luz.

Essas luzes precisam de posicao porque os termos difuso, especular e de sombra dependem da geometria entre o ponto atingido e a luz. A posicao permite calcular o vetor `L`, a distancia ate a luz e o raio de sombra que verifica se algum objeto bloqueia essa luz.

## 5. Modelo de Phong

A funcao principal da entrega 3 e `iluminar_phong`.

Arquivo e linhas: `main.py:175-184`.

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

Aqui o codigo separa os coeficientes do material que entram na equacao de Phong. Cada variavel corresponde a um termo do enunciado:

- `ia`: intensidade da luz ambiente `Ia`;
- `ka`: quanto o material recebe de luz ambiente;
- `kd`: quanto o material espalha luz de forma difusa;
- `ks`: quanto o material gera brilho especular;
- `eta`: expoente que controla a concentracao do brilho.

Depois disso, a cor comeca com a contribuicao ambiente:

```text
ka * Ia
```

O `eta` e calculado com `max(..., 1.0)` para garantir que o expoente de brilho seja sempre positivo, como pede o enunciado.

O `observador` e o vetor `V` da equacao de Phong. Ele aponta do ponto de intersecao para a camera, porque nos raios primarios o espectador e a propria camera. Esse vetor e usado no termo especular: se a direcao de reflexao `R` estiver alinhada com `V`, o observador ve um brilho mais forte naquele ponto.

Depois vem o loop das luzes pontuais:

Arquivo e linhas: `main.py:186-198`.

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

Esse trecho calcula `L`, que e o vetor unitario do ponto ate a luz. Primeiro o codigo calcula `vetor_luz = luz.pos - ponto`; depois separa seu modulo em `distancia_luz` e normaliza a direcao em `direcao_luz`. A distancia e guardada porque o raio de sombra so deve procurar bloqueios entre o ponto e a luz, nao depois da luz.

O produto `N . L` mede o quanto a superficie esta virada para a luz. Se `N` e `L` apontam em direcoes parecidas, o valor e alto e a superficie recebe bastante luz difusa. Se o valor e zero ou negativo, a luz esta de lado ou atras da superficie, entao ela nao deve contribuir naquele ponto.

O teste de sombra acontece antes de somar a luz porque uma luz bloqueada nao deve contribuir nem no termo difuso nem no termo especular. Isso simula o caso fisico em que outro objeto esta entre o ponto iluminado e a fonte luminosa.

Quando a luz contribui, o codigo soma os termos difuso e especular:

Arquivo e linhas: `main.py:200-207`.

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

O vetor `R` e a direcao em que a luz refletiria naquela normal. O vetor `V` aponta para a camera. O produto `R . V` mede se o brilho refletido esta indo na direcao do observador. Quando eles estao alinhados, o ponto recebe um brilho especular forte. Quando nao estao alinhados, o brilho some ou fica fraco.

O `eta`, vindo de `ns`, controla a concentracao desse brilho. Um `eta` maior faz o brilho ficar menor e mais concentrado; um `eta` menor deixa o brilho mais espalhado.

No final, a cor e limitada:

Arquivo e linha: `main.py:209`.

```python
return limitar_cor(cor)
```

Isso evita valores abaixo de `0` ou acima de `1` antes da conversao para RGB de `0` a `255`. Sem esse limite, uma luz muito forte poderia gerar valores maiores que `1`, que depois virariam numeros acima de `255` no arquivo de imagem.

## 6. Sombras

As sombras foram implementadas em `esta_em_sombra`.

Arquivo e linhas: `main.py:164-173`.

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

Esse metodo cria um raio secundario que sai do ponto de intersecao em direcao a luz. A ideia e simples: antes de somar a luz, o codigo pergunta "existe algum objeto entre este ponto e a fonte luminosa?". Se existir, a luz nao chega nesse ponto, entao ele esta em sombra para aquela fonte.

O teste usa `distancia_luz` para aceitar apenas intersecoes que acontecem antes da luz. Se o raio encontrar um objeto depois da luz, esse objeto nao bloqueia a iluminacao e nao deve causar sombra.

O `EPSILON_SOMBRA` serve para deslocar um pouco a origem do raio. Sem isso, por erro numerico, o raio de sombra poderia bater imediatamente na propria superficie que acabou de ser atingida, fazendo o objeto sombrear a si mesmo de forma falsa.

## 7. Normais dos Objetos

Phong depende da normal `N`, porque ela define a orientacao local da superficie. E a normal que diz se a superficie esta virada para a luz, de lado ou de costas. Por isso, sem `N`, nao da para calcular corretamente nem o termo difuso `N . L` nem a reflexao `R` usada no termo especular.

Na esfera:

Arquivo e linhas: `src/Esfera.py:55-57`.

```python
def normal_em(self, ponto: Ponto):
    return (ponto - self.centro).normalizar()
```

A normal da esfera e o vetor que sai do centro em direcao ao ponto da superficie. Isso funciona porque, em uma esfera, a direcao perpendicular a superficie em qualquer ponto e exatamente a direcao do centro para esse ponto.

No plano:

Arquivo e linhas: `src/Plano.py:41-43`.

```python
def normal_em(self, ponto):
    return self.normal
```

O plano tem uma normal constante, entao nao depende do ponto atingido. Qualquer ponto do mesmo plano possui a mesma orientacao de superficie, por isso a mesma normal serve para todos os pixels que atingem esse plano.

Na malha, a normal depende do triangulo atingido:

Arquivo e linhas: `src/Malha.py:307-315`.

```python
def normal_em(self, ponto):
    if self.ultimo_indice_triangulo is None:
        return Vetor(0.0, 1.0, 0.0)

    fallback = self.normais_triangulos[self.ultimo_indice_triangulo]
    normal_obj = self._normal_obj_interpolada(self.ultimo_indice_triangulo, fallback)
    if normal_obj is not None:
        return normal_obj
```

A malha guarda qual triangulo foi atingido durante a intersecao porque cada triangulo pode ter uma orientacao diferente. Se o OBJ tiver normais (`vn`), o codigo usa essas normais interpoladas para obter uma normal mais suave no ponto. Se nao tiver, usa a normal geometrica do triangulo como fallback.

Essa parte e necessaria porque uma malha nao e uma superficie unica simples como uma esfera ou um plano. Ela e formada por varios triangulos, e a iluminacao correta depende de saber exatamente qual triangulo o raio atingiu e qual normal deve ser usada naquele ponto.

## 8. Normal Orientada

Antes de iluminar, o codigo orienta a normal em relacao ao raio da camera.

Arquivo e linhas: `main.py:144-152`.

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

Isso evita usar uma normal apontando para o lado errado. O teste `normal.prodEscalar(raio.direcao) > 0` verifica se a normal esta apontando no mesmo sentido do raio, ou seja, para longe da camera. Nesse caso, ela e invertida para ficar voltada para o lado visivel.

Essa correcao e importante em malhas OBJ, porque a ordem dos vertices pode fazer algumas faces ficarem com a normal invertida. Se a normal usada estiver do lado errado, o produto `N . L` pode ficar negativo mesmo quando a luz deveria iluminar a face.

## 9. Termos Recursivos Ignorados

A equacao completa tambem possui:

```text
kr * Ir + kt * It
```

Nessa parte:

- `Ir` seria a cor RGB retornada por um raio refletido, em `[0, 255]^3`;
- `It` seria a cor RGB retornada por um raio refratado, em `[0, 255]^3`.

Esses termos representam reflexao e refracao. Eles foram deixados de fora porque a entrega 3 pede Phong sem recursao. Para calcular `Ir` e `It`, seria necessario disparar novos raios refletidos e refratados e chamar o ray-casting novamente.

## 10. Arquivos Principais

- `main.py`: contem o fluxo do render, Phong, sombras, busca de intersecao e orientacao da normal.
- `src/Esfera.py`: calcula a normal da esfera.
- `src/Plano.py`: retorna a normal constante do plano.
- `src/Malha.py`: guarda o triangulo atingido e calcula a normal da malha.
- `utils/Scene/sceneParser.py`: le `kd`, `ka`, `ks`, `kr`, `kt` e `ns`.
- `utils/Scene/sceneSchema.py`: define os dados de material e luz usados na cena.

## Resumo

A entrega 3 transforma o ray-casting simples em um renderizador com iluminacao local. O programa ainda nao faz reflexao ou refracao recursiva, mas agora calcula luz ambiente, difusa, especular e sombras. Com isso, os objetos deixam de aparecer apenas com cor plana e passam a ter volume visual, brilho e regioes escurecidas quando a luz e bloqueada.
