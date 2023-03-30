# -*- coding: utf-8 -*-
"""PredicaoDeSinais.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1hBvPM_Bq7BhH8O7L-f_Q3zodmOePGEzV
"""

# Importando as bibliotecas
import os
import pathlib
import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers
from tensorflow.keras import models
from IPython import display

# Garantia de aleatoriedade
seed = 77
tf.random.set_seed(seed)
np.random.seed(seed)

# Importar os Dados
caminho_do_conjunto_de_dados = 'data/mini_speech_commands'
dir_dados = pathlib.Path(caminho_do_conjunto_de_dados)
if not dir_dados.exists():
  tf.keras.utils.get_file(
      'mini_speech_commands.zip',
       origin='http://storage.googleapis.com/download.tensorflow.org/data/mini_speech_commands.zip',
       extract=True,
       cache_dir='.', cache_subdir='data')

# Visualizar os dados
comandos = np.array(tf.io.gfile.listdir(str(dir_dados)))
comandos = comandos[comandos != 'README.md']
print('Comandos: {}'.format(comandos))

# Embaralhar os dados
nomes_arquivos = tf.io.gfile.glob(str(dir_dados) + '/*/*')
nomes_arquivos = tf.random.shuffle(nomes_arquivos)
qtde_amostras = len(nomes_arquivos)
print('Quantidade total de amostras: {}'.format(qtde_amostras))
print('Quantidade de exemplos por rótulos:', len(tf.io.gfile.listdir(str(dir_dados/comandos[0]))))
print('Exemplo de arquivo tensor:', nomes_arquivos[1])

# Separação dos dados
arquivos_treinamento = nomes_arquivos[:6400]
arquivos_validacao = nomes_arquivos[6400: 6400 + 800]
arquivos_teste = nomes_arquivos[-800:]
print('Tamanho do conjunto de treinamento: {}'.format(len(arquivos_treinamento)))
print('Tamanho do conjunto de validação: {}'.format(len(arquivos_validacao)))
print('Tamanho do conjunto de testes: {}'.format(len(arquivos_teste)))

# Decodificar os dados
arquivo_de_teste = tf.io.read_file(caminho_do_conjunto_de_dados+'/down/0a9f9af7_nohash_0.wav')
audio_de_teste, _ = tf.audio.decode_wav(contents = arquivo_de_teste)
audio_de_teste.shape
def audio_decodificado(audio_binario):
  audio, _ = tf.audio.decode_wav(contents = audio_binario)
  return tf.squeeze(audio, axis=-1)

# Rotular os dados
def obter_rotulo(caminho_do_arquivo):
  partes = tf.strings.split(input=caminho_do_arquivo, sep=os.path.sep)
  return partes[-2]

# Associar o rótulo as ondas de áudio
def obter_onda_e_rotulo(caminho_do_arquivo):
  rotulo = obter_rotulo(caminho_do_arquivo)
  audio_binario = tf.io.read_file(caminho_do_arquivo)
  onda = audio_decodificado(audio_binario)
  return onda, rotulo

# Chamar a função que rotula os dados por meio do mapeamento dos arquivos de treinamento
AUTOTUNE = tf.data.AUTOTUNE
arquivos_do_conjunto_treinamento = tf.data.Dataset.from_tensor_slices(arquivos_treinamento)
ondas_do_conjunto_treinamento = arquivos_do_conjunto_treinamento.map(map_func = obter_onda_e_rotulo, num_parallel_calls = AUTOTUNE)

# Calcular o Epectrograma 
def obter_espectograma(onda):
  tamanho_entrada = 16000
  onda = onda[:tamanho_entrada]
  zero_padding = tf.zeros(
       [16000] - tf.shape(onda),
       dtype=tf.float32)
  onda = tf.cast(onda, dtype=tf.float32)
  comprimento_igual = tf.concat([onda, zero_padding], 0)  
  espectrograma = tf.signal.stft(
       comprimento_igual, frame_length=255, frame_step=128)
  espectrograma = tf.abs(espectrograma)
  espectrograma = espectrograma[..., tf.newaxis]
  return espectrograma

# Função para imprimir o Espectrograma
def grafico_espectrograma(espectrograma, ax):
  if len(espectrograma.shape) > 2:
    assert len(espectrograma.shape) == 3
    espectrograma = np.squeeze(espectrograma, axis=-1)
  log_espectograma = np.log(espectrograma.T + np.finfo(float).eps)
  altura = log_espectograma.shape[0]
  largura = log_espectograma.shape[1]
  X = np.linspace(0, np.size(log_espectograma), num=largura, dtype=int)
  Y = range(altura)
  ax.pcolormesh(X, Y, log_espectograma)

fig, axes = plt.subplots(2, figsize=(12, 8))
escala_de_tempo = np.arange(onda.shape[0])
axes[0].plot(escala_de_tempo, onda.numpy())
axes[0].set_title('Formato da onda de áudio')
axes[0].set_xlim([0, 16000])
 
grafico_espectrograma(espectrograma.numpy(), axes[1])
axes[1].set_title('Espectrograma')
plt.show()

# Explorar os dados
for onda, rotulo in ondas_do_conjunto_treinamento.take(3):
  rotulo = rotulo.numpy().decode('utf-8')
  espectrograma = obter_espectograma(onda)
print('Rótulo: {}'.format(rotulo))
print('Formato da onda: {}'.format(onda.shape))
print('Formato do espectrograma: {}'.format(espectrograma.shape))
print('Prezado estudante, pressione o play para escutar o áudio.')
display.display(display.Audio(onda, rate=16000))

# Associar o Espcetrograma com os rótulos
def obter_espectrograma_e_rotulo_id(audio, rotulo):
  espectrograma = obter_espectograma(audio)
  rotulo_id = tf.argmax(rotulo == comandos)
  return espectrograma, rotulo_id
espectrograma_do_conjunto_treinamento = ondas_do_conjunto_treinamento.map(  map_func=obter_espectrograma_e_rotulo_id, num_parallel_calls=AUTOTUNE)

# Prepara os dados para treinamento - representados por espectrograma
def conjunto_de_dados_preprocessados(arquivos):
  arquivos_conjunto_de_treinamento = tf.data.Dataset.from_tensor_slices(arquivos)
  saida = arquivos_conjunto_de_treinamento.map(
       map_func=obter_onda_e_rotulo,
       num_parallel_calls=AUTOTUNE)
  saida = saida.map(
       map_func = obter_espectrograma_e_rotulo_id,
       num_parallel_calls = AUTOTUNE)
  return saida

treinamento = espectrograma_do_conjunto_treinamento
validacao = conjunto_de_dados_preprocessados(arquivos_validacao)
teste = conjunto_de_dados_preprocessados(arquivos_teste)

batch_size = 64
treinamento = treinamento.batch(batch_size)
validacao = validacao.batch(batch_size)

treinamento = treinamento.cache().prefetch(AUTOTUNE)
validacao = validacao.cache().prefetch(AUTOTUNE)

"""**ALGORITMO DE PREDIÇÃO**"""

# Construir o modelo
for espectrograma, _ in espectrograma_do_conjunto_treinamento.take(1):
  formato_entrada = espectrograma.shape
print('Formato da entrada: {}'.format(formato_entrada))
num_rotulos = len(comandos)
camada_normalizada = layers.Normalization()
camada_normalizada.adapt(data=espectrograma_do_conjunto_treinamento.map(map_func=lambda spec, label: spec))
modelo = models.Sequential([
     layers.Input(shape=formato_entrada),
     layers.Resizing(32, 32),    
     camada_normalizada,
     layers.Conv2D(32, 3, activation='relu'),
     layers.Conv2D(64, 3, activation='relu'),
     layers.MaxPooling2D(),
     layers.Dropout(0.25),
     layers.Flatten(),
     layers.Dense(128, activation='relu'),
     layers.Dropout(0.5),
     layers.Dense(num_rotulos),
 ])
modelo.summary()

# Configurar e compilar o otimizador
modelo.compile(
     optimizer=tf.keras.optimizers.Adam(),
     loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
     metrics=['accuracy'],
 )

# Treinar o modelo
EPOCAS = 100
historico = modelo.fit(
     treinamento,
     validation_data=validacao,
     epochs=EPOCAS,
     callbacks=tf.keras.callbacks.EarlyStopping(verbose=1, patience=2),
)

# Gráficos de Desempenho
metricas = historico.history
plt.plot(historico.epoch, metricas['loss'], metricas['val_loss'])
plt.legend(['perda treinamento', 'perda validação'])
plt.show()

# Avaliar o desempenho do modelo
teste_audio = []
teste_rotulos = []
for audio, rotulo in teste:
  teste_audio.append(audio.numpy())
  teste_rotulos.append(rotulo.numpy())
teste_audio = np.array(teste_audio)
teste_rotulos = np.array(teste_rotulos)

# Testar o modelo
arquivo_de_amostra = dir_dados/'no/01bb6a2a_nohash_0.wav'
amostra = conjunto_de_dados_preprocessados([str(arquivo_de_amostra)])
for espectrograma, rotulo in amostra.batch(1):
   predicao = modelo(espectrograma)
   plt.bar(comandos, tf.nn.softmax(predicao[0]))
   #plt.title(f 'Predições para '{comandos[rotulo[0]]}' ')
   plt.show()