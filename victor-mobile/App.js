import React,
{
  useState,
  useEffect,
  useRef
} from 'react';
import {
  StyleSheet,
  Text,
  View,
  Button,
  PermissionsAndroid,
  Platform
} from 'react-native';
import {
  initWhisper,
  releaseAllWhisper,
  transcribeRealtime
} from 'whisper.rn';
import RNFS from 'react-native-fs';

const MODEL_URL = 'https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en.bin';
const MODEL_FILE_PATH = `${RNFS.DocumentDirectoryPath}/ggml-tiny.en.bin`;

export default function App() {
  const [status, setStatus] = useState('Model not downloaded');
  const [isModelDownloaded, setIsModelDownloaded] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [transcription, setTranscription] = useState('');
  const whisperContext = useRef(null);

  useEffect(() => {
    async function checkModel() {
      const modelExists = await RNFS.exists(MODEL_FILE_PATH);
      if (modelExists) {
        setStatus('Model is ready');
        setIsModelDownloaded(true);
        await initializeWhisper();
      }
    }
    checkModel();

    return () => {
      releaseAllWhisper();
    };
  }, []);

  const initializeWhisper = async () => {
    try {
      if (whisperContext.current) {
        await whisperContext.current.release();
        whisperContext.current = null;
      }
      const context = await initWhisper({
        filePath: MODEL_FILE_PATH
      });
      whisperContext.current = context;
      setStatus('Whisper initialized');
    } catch (e) {
      console.error(e);
      setStatus('Error initializing whisper');
    }
  };

  const downloadModel = async () => {
    setStatus('Downloading model...');
    const {
      promise
    } = RNFS.downloadFile({
      fromUrl: MODEL_URL,
      toFile: MODEL_FILE_PATH,
    });
    try {
      const result = await promise;
      if (result.statusCode === 200) {
        setStatus('Model downloaded');
        setIsModelDownloaded(true);
        await initializeWhisper();
      } else {
        setStatus(`Download failed: ${result.statusCode}`);
      }
    } catch (e) {
      console.error(e);
      setStatus('Download error');
    }
  };

  const requestPermissions = async () => {
    if (Platform.OS === 'android') {
      try {
        const granted = await PermissionsAndroid.request(
          PermissionsAndroid.PERMISSIONS.RECORD_AUDIO, {
            title: 'Microphone Permission',
            message: 'Victor needs access to your microphone to transcribe your voice.',
            buttonNeutral: 'Ask Me Later',
            buttonNegative: 'Cancel',
            buttonPositive: 'OK',
          },
        );
        return granted === PermissionsAndroid.RESULTS.GRANTED;
      } catch (err) {
        console.warn(err);
        return false;
      }
    }
    return true;
  };

  const handleTranscription = async () => {
    if (isTranscribing) {
      // Stop transcription
      if (whisperContext.current) {
        await whisperContext.current.stopRealtimeTranscribe();
      }
      setIsTranscribing(false);
      setStatus('Transcription stopped');
    } else {
      // Start transcription
      const hasPermission = await requestPermissions();
      if (!hasPermission) {
        setStatus('Microphone permission denied');
        return;
      }

      if (!whisperContext.current) {
        setStatus('Whisper not initialized');
        return;
      }

      try {
        const {
          stop,
          subscribe
        } = await transcribeRealtime({
          whisperContext: whisperContext.current,
          language: 'en',
          onTranscription: (evt) => {
            setTranscription(evt.text);
          },
        });

        subscribe((evt) => {
          setIsTranscribing(evt.isCapturing);
          if (!evt.isCapturing) {
            setStatus('Transcription stopped');
          }
        });

        setIsTranscribing(true);
        setStatus('Transcribing...');
      } catch (e) {
        console.error(e);
        setStatus('Error starting transcription');
      }
    }
  };

  return ( <
    View style = {
      styles.container
    } >
    <
    Text style = {
      styles.title
    } > Victor Mobile PoC < /Text> <
    Text style = {
      styles.status
    } > Status: {
      status
    } < /Text> {
      !isModelDownloaded && ( <
        Button title = "Download Model"
        onPress = {
          downloadModel
        }
        />
      )
    } {
      isModelDownloaded && ( <
        Button title = {
          isTranscribing ? 'Stop Transcribing' : 'Start Transcribing'
        }
        onPress = {
          handleTranscription
        }
        />
      )
    } <
    Text style = {
      styles.transcriptionTitle
    } > Transcription: < /Text> <
    Text style = {
      styles.transcription
    } > {
      transcription
    } < /Text> <
    /View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 20,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 20,
  },
  status: {
    fontSize: 18,
    marginVertical: 10,
  },
  transcriptionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginTop: 20,
  },
  transcription: {
    fontSize: 16,
    marginTop: 10,
    textAlign: 'center',
  },
});
