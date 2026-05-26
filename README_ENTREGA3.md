# Entrega 3 - Iluminacao de Phong e Sombras

Esta entrega adiciona iluminacao local ao ray-casting que ja existia. Antes, quando um raio acertava um objeto, o programa retornava diretamente a cor difusa do material. Agora, para cada pixel atingido, o programa calcula a cor usando o modelo de Phong sem recursao e tambem verifica sombras.

## O que foi alterado nesta etapa

### 1. Calculo de cor por Phong no `main.py`

Foi adicionada a funcao `iluminar_phong`, responsavel por calcular a cor final do ponto de intersecao.

Ela usa os termos pedidos na entrega:

- `ka * Ia`: contribuicao da luz ambiente.
- `Il * kd * (N . L)`: contribuicao difusa de cada luz.
- `Il * ks * (R . V)^eta`: contribuicao especular de cada luz.

O motivo dessa alteracao e que o ray-casting anterior apenas descobria qual objeto estava visivel. Para a etapa 3, isso nao basta: depois de encontrar o objeto mais proximo, e necessario calcular como a luz chega naquele ponto da superficie.

Os termos de reflexao e transmissao:

- `kr * Ir`
- `kt * It`

foram deixados de fora propositalmente, porque o enunciado diz que reflexoes e refracoes serao tratadas em outra etapa.

### 2. Raios de sombra

Foi adicionada a funcao `esta_em_sombra`.

Para cada luz da cena, o programa cria um raio que sai do ponto de intersecao em direcao a essa luz. Se esse raio bater em algum objeto antes de chegar na luz, a contribuicao daquela luz e ignorada para esse ponto.

Isso foi necessario porque, sem sombra, todos os pontos visiveis receberiam luz mesmo quando existe outro objeto bloqueando a fonte luminosa. Com essa verificacao, o programa passa a diferenciar regioes iluminadas e regioes ocultas da luz.

Tambem foi usado um pequeno `EPSILON_SOMBRA` para deslocar o inicio do raio de sombra um pouco para fora da superficie. Isso evita que o raio de sombra intercepte imediatamente o mesmo objeto por erro numerico.

### 3. Normal no ponto de intersecao

O modelo de Phong precisa da normal `N` no ponto atingido pelo raio. Por isso, cada tipo de objeto agora sabe devolver sua normal:

- `Esfera.normal_em(ponto)`: calcula a normal usando a direcao do centro da esfera ate o ponto.
- `Plano.normal_em(ponto)`: retorna a normal constante do plano.
- `Malha.normal_em(ponto)`: calcula a normal da malha no triangulo atingido.

Essa mudanca foi necessaria porque a iluminacao difusa e especular depende diretamente do angulo entre a superficie, a luz e a camera. Sem normal, nao ha como calcular `N . L` nem o vetor de reflexao `R`.

### 4. Normais interpoladas para malhas

Na malha, a intersecao agora guarda:

- o indice do triangulo atingido;
- as coordenadas baricentricas do ponto dentro desse triangulo.

Com isso, `Malha.normal_em` interpola as normais medias dos vertices do triangulo atingido. O resultado e uma normal mais adequada para iluminacao do que usar apenas uma normal fixa por face.

Isso foi feito porque o enunciado pede normais dos vertices como media das normais dos triangulos compartilhados. Usar essas normais na iluminacao deixa a malha pronta para sombreamento mais suave.

### 5. Busca da intersecao mais proxima separada

Foi adicionada a funcao `encontrar_intersecao`.

Antes, o loop principal guardava apenas o material do objeto atingido. Agora ele precisa guardar o objeto inteiro e a distancia `t`, porque a etapa 3 precisa calcular:

- o ponto exato da intersecao;
- a normal naquele ponto;
- os raios de sombra;
- a cor final usando os dados do material.

Separar essa busca deixou o fluxo mais claro: primeiro o programa encontra o objeto visivel; depois calcula a iluminacao desse ponto.

### 6. Leitura dos coeficientes de material

O parser de cena foi ajustado para aceitar `kd` como alias de `color`.

No projeto base, a cor difusa ja vinha em `material.color`. No enunciado da etapa 3, esse mesmo valor aparece como `kd`. Para suportar os dois formatos de JSON, o parser agora entende:

- `color`: cor difusa usada nas cenas antigas;
- `kd`: coeficiente difuso no formato do enunciado.

Tambem foi ajustado o valor padrao de `ns` para `1.0`, garantindo que o coeficiente de rugosidade/brilho seja positivo quando a cena nao informar esse campo explicitamente.

### 7. Orientacao da normal para a camera

Foi adicionada a funcao `normal_orientada`.

Ela garante que a normal usada no Phong esteja apontando contra o raio primario quando necessario. Isso evita resultados estranhos em faces cujo sentido geometrico esteja invertido em relacao a camera.

Essa decisao e importante principalmente para malhas OBJ, porque a ordem dos vertices das faces pode fazer algumas normais ficarem apontadas para o lado oposto ao observador.

## Fluxo atual do render

Para cada pixel:

1. O programa gera um raio primario da camera.
2. Procura o objeto mais proximo interceptado por esse raio.
3. Se nao houver intersecao, escreve preto.
4. Se houver intersecao, calcula o ponto atingido.
5. Calcula a normal no ponto.
6. Soma a luz ambiente.
7. Para cada luz:
   - calcula o vetor ate a luz;
   - dispara um raio de sombra;
   - se nao houver bloqueio, soma os termos difuso e especular de Phong.
8. Limita a cor final ao intervalo `[0, 1]`.
9. Converte a cor para `[0, 255]` no arquivo PPM.

## Arquivos alterados nesta etapa

- `main.py`: adiciona Phong, sombras, busca de intersecao, conversao de cores e orientacao de normal.
- `src/Esfera.py`: adiciona normal no ponto da esfera.
- `src/Plano.py`: adiciona normal no ponto do plano.
- `src/Malha.py`: guarda dados da intersecao e calcula normal interpolada para iluminacao.
- `utils/Scene/sceneParser.py`: aceita `kd` como coeficiente difuso.
- `utils/Scene/sceneSchema.py`: ajusta `ns` padrao para valor positivo.

## Verificacoes feitas

Foram executados testes de compilacao e renderizacao:

```bash
python -m compileall main.py src utils
python main.py utils/input/caso3.json /private/tmp/ray_etapa3_caso3_final.ppm
```

Tambem foram testadas cenas com malhas e transformacoes durante a implementacao para garantir que a entrega 2 continuou funcionando junto com a nova iluminacao.
