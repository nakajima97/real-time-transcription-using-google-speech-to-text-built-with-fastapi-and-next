import socketio
from google.cloud import speech
import asyncio

# Setup socket.io
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins=[])
app_socketio = socketio.ASGIApp(sio)

# アクティブなストリームハンドラを保持
stream_handlers = {}


@sio.event
async def connect(sid, environ):
    """socketioのconnectイベント"""
    print("connect ", sid)


@sio.event
async def disconnect(sid):
    """socketioのdisconnectイベント"""
    print(f"disconnect {sid}")
    if sid in stream_handlers:
        await stream_handlers[sid].stop_stream()
        del stream_handlers[sid]


@sio.on("startGoogleCloudStream")
async def start_recognition(sid):
    """音声認識開始イベント"""
    print(f"Starting recognition for {sid}")
    if sid not in stream_handlers:
        stream_handlers[sid] = AudioStreamHandler(sid)
    await stream_handlers[sid].handle_queue()


@sio.on("stopGoogleCloudStream")
async def stop_recognition(sid):
    """音声認識終了イベント"""
    print(f"Stopping recognition for {sid}")
    if sid in stream_handlers:
        await stream_handlers[sid].stop_stream()


@sio.on("send_audio_data")
async def send_audio_data(sid, data):
    """音声データ送信イベント"""
    if sid in stream_handlers:
        handler = stream_handlers[sid]
        await handler.queue.put(data)


class AudioStreamHandler:
    def __init__(self, sid: str):
        """
        音声ストリーム処理を管理するクラス

        Args:
            sid (str): Socket.IOのセッションID
        """
        self.sid = sid
        self.queue = asyncio.Queue()
        self.client = speech.SpeechAsyncClient()
        self.streaming_config = speech.StreamingRecognitionConfig(
            config=speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code="ja-JP",
                enable_automatic_punctuation=True,
            ),
            interim_results=True,
        )
        self._is_streaming = True

    async def process_queue(self):
        """
        キューからデータを取り出して非同期イテレーターとして返すメソッド
        """
        yield speech.StreamingRecognizeRequest(streaming_config=self.streaming_config)

        while self._is_streaming:
            data = await self.queue.get()
            audio_content = data["audio"]
            yield speech.StreamingRecognizeRequest(audio_content=audio_content)

        # 終了処理
        print(f"process_queue stop. {self.sid}")

    async def handle_queue(self):
        try:
            stream = await self.client.streaming_recognize(
                requests=self.process_queue()
            )
            async for response in stream:
                if not response:
                    print("No response")
                    continue

                if not response.results:
                    print("No results")
                    continue

                result = response.results[0]

                if not result.alternatives:
                    print("No alternatives")
                    continue

                for result in response.results:
                    transcription = result.alternatives[0].transcript
                    is_final = result.is_final

                    # 結果をクライアントに送信
                    await sio.emit(
                        "receive_audio_text",
                        {"text": transcription, "isFinal": is_final},
                        room=self.sid,
                    )
        except Exception as e:
            print(f"An error occurred in handle_queue: {e}")
        finally:
            print(f"handle_queue finish {self.sid}")

    async def stop_stream(self):
        """ストリーミングを停止する"""
        self._is_streaming = False
        # キューに残っているデータを処理するためにNoneをpush
        await self.queue.put({"audio": b""})
        print(f"stop_stream {self.sid}")