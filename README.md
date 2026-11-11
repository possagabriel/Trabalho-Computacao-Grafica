# Base Aurora — inspeção e escolta aérea

Trabalho prático de Computação Gráfica, 2026/02. Aplicação **Python + Pygame + OpenGL 3.3**, com drone de quatro hélices e helicóptero estilizado, modelados por composição de primitivas. A animação representa uma missão de encontro, inspeção e escolta em uma base aérea.

![Cena da Base Aurora durante a inspeção](docs/preview.png)

A versão revisada inclui inclinação durante as manobras, aceleração e desaceleração dos rotores, protetores de hélice, detalhes de cabine e base, painéis solares texturizados e antisserrilhamento MSAA. O painel tem mapa de posições, barras de potência e uma linha do tempo clicável; a câmera pode acompanhar as aeronaves.

## Integrantes e temas

Os temas **3 e 4** foram informados pelo solicitante. Os nomes e a distribuição efetiva das contribuições não foram informados; devem ser preenchidos pela dupla antes da entrega.

| Integrante | Identificação | Tema sorteado |
|---|---|---|
| Integrante do drone | **Gabriel Possa Lima** | **3 — Drone de quatro hélices** |
| Integrante do helicóptero | **Darlan José dos Santos** | **4 — Helicóptero estilizado** |

## Instalação e execução

Requisitos: Python **3.10 ou superior**, driver com **OpenGL 3.3 core** e ambiente gráfico. O projeto inclui os componentes do framework, shaders e imagens; não baixa recursos durante a execução.

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

Windows (PowerShell):

```powershell
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe main.py
```

`pygame-ce` é a distribuição comunitária de Pygame e fornece o módulo `pygame`. Não instale `pygame` e `pygame-ce` juntos no mesmo ambiente. As versões efetivamente testadas estão em [requirements-tested.txt](requirements-tested.txt).

As texturas são resolvidas a partir da pasta do projeto; também é possível executar `main.py` por caminho absoluto. `F12` salva capturas em `captures/` no diretório de execução.

## Cena e interação

O helicóptero laranja decola do heliponto H e aproxima-se do ponto de encontro. Só após sua chegada o drone verde decola do heliponto D. O helicóptero aguarda enquanto o drone realiza uma volta de inspeção, orientando sua câmera para a aeronave. Ao concluir a volta, os dois avançam em formação, retornam e pousam. O ciclo de **37 segundos** repete-se continuamente.

| Intervalo | Etapa | Dependência entre os elementos |
|---|---|---|
| 0–2 s | Preparação | Os dois aguardam a autorização da base. |
| 2–6 s | Decolagem | Helicóptero sobe; drone aguarda. |
| 6–11 s | Aproximação | Helicóptero alcança o ponto de encontro. |
| 11–14 s | Encontro | Chegada do helicóptero libera a decolagem do drone. |
| 14–20 s | Inspeção | Drone contorna o helicóptero, que permanece em espera. |
| 20–26 s | Escolta | Fim da inspeção libera a partida; drone mantém deslocamento relativo constante. |
| 26–31 s | Retorno | Fim da escolta inicia o retorno de ambos. |
| 31–35 s | Pouso | As duas aeronaves descem aos seus helipontos. |
| 35–37 s | Conclusão | Preparação para repetir o ciclo. |

O controlador compartilhado impede que a inspeção aconteça antes do encontro ou que o helicóptero parta durante a inspeção. As posições são funções do tempo em segundos. Não há simulação física nem detecção de colisão, conforme permitido no enunciado.

## Controles

| Tecla | Ação |
|---|---|
| Espaço | Pausar/retomar posições, hélices e sequência; câmera continua livre. |
| Setas | Orbitar a câmera horizontal/verticalmente. |
| Arrastar com botão esquerdo | Orbitar a câmera com o mouse. |
| Clique na linha do tempo | Escolher a etapa e o instante, inclusive durante a pausa. |
| F ou botão “Seguir aeronaves” | Ativar/desativar o acompanhamento suave da formação. W/A/S/D libera o acompanhamento. |
| W / A / S / D | Deslocar o alvo da câmera no plano horizontal. |
| Q / E ou roda do mouse | Afastar/aproximar a câmera. |
| 1 / 2 / 3 | Vista geral, encontro e vista superior. |
| C | Restaurar a câmera inicial. |
| R | Reiniciar a missão, preservando o estado de pausa. |
| N | Saltar para a próxima etapa, inclusive durante a pausa. |
| + / − | Mudar velocidade entre 0,25× e 4×. |
| P | Ligar/desligar sombra projetada para comparar com o sombreamento. |
| B | Ligar/desligar faixas procedurais de segurança do hangar. |
| H | Exibir/ocultar ajuda. |
| Tab | Ocultar/exibir o painel para uma apresentação sem sobreposições. |
| F12 | Salvar captura PNG. |
| Esc | Encerrar. |

O painel mostra a etapa, sua dependência, o progresso, as alturas das origens dos modelos e a distância entre elas. As barras abaixo das aeronaves indicam a potência normalizada dos rotores; o mapa acompanha suas posições em XZ. As unidades da cena são tratadas como metros para fins ilustrativos. Os cliques no painel são ajustados à escala quando a janela é redimensionada.

## Correspondência com os requisitos do PDF

| Requisito | Implementação e localização |
|---|---|
| 1. Dois temas reconhecíveis no ambiente | `app/models.py`: `Drone`, `Helicopter`; `app/scene.py`: `build_scene`. Quatro motores/hélices, câmera e patins no drone; cabine, cauda, rotor principal, rotor de cauda e patins no helicóptero. |
| 2. Animação temporal e interação | `app/mission.py`: `Mission.advance`, `sample`, `STAGES`; `app/scene.py`: `apply_mission`; rotores em `app/models.py`. |
| 3. Translação, rotação, escala e hierarquia | `framework/core.py`: `Object3D.local_matrix`, `world_matrix`, `add`, `meshes`; rotores filhos dos modelos. |
| 4. Perspectiva, teclado e pausa | `framework/core.py`: `Camera`; eventos e relógio em `main.py`. |
| 5. Textura de imagem e UVs | PNGs em `assets/textures/`; `framework/geometry.py`: coluna UV; `Renderer.texture`; shaders `lit.vert` e `lit.frag`. |
| 6. Luz direcional e normais | `Shadow.direction`; matriz normal inversa transposta em `Renderer.render`; iluminação ambiente, difusa e especular em `lit.frag`. |
| 7. Shadow mapping, seção 6.9 | `framework/renderer.py`: `Shadow`, `Renderer.render`; `depth.vert/.frag`; função `shadowVisibility` em `lit.frag`. FBO de profundidade, câmera da luz e comparação no passe da câmera. |
| Explicação de shaders, atributos e uniforms | [Guia técnico](docs/GUIA_TECNICO.md), com tabelas e fórmulas aplicadas. |
| Componentes do framework | Pasta `framework/`; [adaptações e correspondência com o livro](docs/FRAMEWORK.md). |
| Bônus opcional | Faixas de segurança calculadas no fragment shader por UVs, sem imagem: `proceduralEnabled` em `lit.frag`. O bônus depende da avaliação do professor. |
| Entrega e apresentação | Este README, dependências, recursos locais, declaração de IA, testes e [roteiro de 10 minutos](docs/APRESENTACAO.md). |

## Organização

```text
main.py                    janela, eventos, loop e controles
app/models.py              modelos hierárquicos das aeronaves
app/scene.py               base aérea e aplicação das poses
app/mission.py             sequência temporal independente da renderização
app/hud.py                 painel e ajuda
framework/core.py          Object3D, Scene, Mesh, Material, Camera
framework/matrix.py        transformações e projeções
framework/geometry.py      caixas, esferas e cilindros/cones truncados
framework/window.py        contexto OpenGL com MSAA e fallback
framework/renderer.py      shaders, VAO/VBO, texturas e shadow mapping
shaders/                   programas GLSL separados e comentados
assets/textures/            cinco imagens PNG incluídas
tools/generate_textures.py  geração reprodutível das imagens
tools/validate_render.py    teste de integração com OpenGL real
tools/package_project.py    gera arquivo ZIP para entrega
tests/                     testes de matemática, geometria e coordenação
docs/                      guia técnico, roteiro e evidências
```

## Verificação

```bash
python -m unittest discover -s tests -v
python tools/validate_render.py
python main.py --headless --time 16 --screenshot captures/inspecao.png
```

O teste OpenGL usa o backend `offscreen` do SDL, disponível no ambiente Linux testado. Em sistemas sem esse backend, use a aplicação na janela e o checklist do roteiro. Os testes unitários não precisam de janela ou contexto OpenGL.

Para conferir um ciclo por tempo simulado:

```bash
python main.py --headless --frames 223 --fixed-dt 0.1666666667 --shadow-size 1024
```

Para uma comparação visual de sombras, use `--time 16 --fixed-dt 0 --frames 1 --screenshot ...`, com e sem `--no-shadows`. Para computadores mais lentos, use `python main.py --shadow-size 1024 --size 960 640`.

`--msaa 0` desliga o antisserrilhamento; o padrão é 4 amostras, com fallback automático se o driver não suportar. `--view encontro` inicia com enquadramento próximo. `--screenshot arquivo.png`, sem `--frames`, captura um quadro e encerra.

```bash
python main.py --view encontro --time 16
python main.py --headless --view encontro --time 16 --screenshot captures/encontro.png
```

Resultados registrados em [VALIDACAO.md](docs/VALIDACAO.md). A execução interativa com teclado e driver da máquina de apresentação deve ser conferida antes da aula.

## Contribuições individuais — preencher após a revisão

Não foram fornecidas contribuições humanas verificáveis. A tabela é uma proposta de divisão da **revisão, adaptação e apresentação**, não uma declaração de autoria já realizada.

| Integrante | Responsabilidade sugerida | Contribuição efetivamente realizada |
|---|---|---|
| Tema 3 — drone | Revisar `Drone`, quatro rotores, câmera de inspeção, UVs e texturas; explicar a inspeção. | **PREENCHER COM O TRABALHO REALIZADO** |
| Tema 4 — helicóptero | Revisar `Helicopter`, hierarquia dos rotores, câmera, iluminação e shadow mapping. | **PREENCHER COM O TRABALHO REALIZADO** |
| Ambos | Revisar controlador integrado, testes, escolhas gráficas e apresentação; executar na máquina da aula. | **PREENCHER COM O TRABALHO REALIZADO** |

## Fontes e origem dos recursos

- **Enunciado:** `Trabalho - Computacao Grafica.pdf`, fornecido pelo solicitante.
- **Referência conceitual:** STEMKOSKI, Lee; PASCALE, Michael. *Developing Graphics Frameworks with Python and OpenGL*. CRC Press, 2022. [DOI 10.1201/9781003181378](https://doi.org/10.1201/9781003181378). Arquitetura de grafo de cena, transformações, texturas e shadow mapping; relação dos componentes em `docs/FRAMEWORK.md`.
- **Referência pública dos autores:** [stemkoski/three.py](https://github.com/stemkoski/three.py), consultada para a organização de cena, câmera, malhas, materiais e luz direcional. O projeto entregue não incorpora esse repositório nem depende dele.
- **Código desta entrega:** reimplementação didática parcial da arquitetura do framework, com adaptações documentadas; não é uma cópia literal nem uma distribuição oficial dos arquivos do livro.
- **Modelos:** composição programática de primitivas locais; nenhum modelo 3D baixado.
- **Texturas:** imagens originais geradas por `tools/generate_textures.py`, com ruído de semente fixa e desenhos 2D. Não foram utilizadas imagens externas. Texto rasterizado com a fonte padrão distribuída pelo Pygame.

## Declaração de uso de inteligência artificial

Foi utilizado **OpenAI Codex**, nesta sessão, para ler os requisitos do PDF, propor a base aérea, implementar o framework parcial, os dois modelos, o controlador de missão, os shaders, as texturas programáticas, o painel, os testes e a documentação, e para revisar falhas encontradas na renderização.

**Escopo do apoio:** todos os arquivos de código, shaders, recursos gerados e documentos novos desta entrega foram desenvolvidos com apoio da ferramenta. O PDF do enunciado foi fornecido pelo solicitante. Esta declaração não atesta revisão humana já realizada. A dupla deve revisar o código, registrar suas contribuições reais e ser capaz de explicar a aplicação integrada, como exige o enunciado.

## Empacotamento e pendências pessoais

```bash
python tools/package_project.py
```

O comando cria `dist/base-aurora-entrega.zip` com fontes, framework, shaders, texturas, testes e documentação, sem `.venv`, caches ou capturas temporárias. Antes da entrega, preencher os nomes, matrículas e contribuições; executar a aplicação no computador da apresentação e ensaiar o roteiro com os dois integrantes.

Para validar, empacotar e enviar os seis commits explicativos à branch atual no repositório informado, use `bash tools/publish_github.sh`. Veja as verificações e os passos em [PUBLICACAO.md](docs/PUBLICACAO.md). Esse envio precisa ser feito em um terminal com escrita na pasta `.git`, rede e autenticação no GitHub.

## Diagnóstico

- `No module named ...`: usar o mesmo Python para instalar e executar (`python -m pip install -r requirements.txt`).
- Falha ao criar contexto OpenGL: conferir driver e suporte a OpenGL 3.3 core; `SDL_VIDEODRIVER=dummy` não fornece OpenGL.
- Sessão Linux sem display: `--headless` utiliza SDL offscreen, quando suportado; a execução normal precisa de sessão gráfica.
- Desempenho baixo: reduzir janela e resolução das sombras. A taxa de quadros pode variar, mas o percurso continua baseado em segundos.
- `--headless` é um modo de teste, não uma substituição da apresentação interativa.
