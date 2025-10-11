import React, { useEffect, useState } from 'react';
import { SafeAreaView, Text, StyleSheet } from 'react-native';

const API_URL = process.env.API_URL || 'http://localhost:8000/api/prompts';
const AUTH_TOKEN = process.env.AUTH_TOKEN || '';

export default function App() {
  const [prompt, setPrompt] = useState('Loading...');

  useEffect(() => {
    async function loadPrompt() {
      try {
        const res = await fetch(API_URL, {
          headers: {
            Authorization: `Bearer ${AUTH_TOKEN}`,
          },
        });
        const data = await res.json();
        setPrompt(data.prompt || 'No prompt');
      } catch (err) {
        setPrompt('Failed to fetch prompt');
      }
    }
    loadPrompt();
  }, []);

  return (
    <SafeAreaView style={styles.container}>
      <Text style={styles.prompt}>{prompt}</Text>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#000',
  },
  prompt: {
    color: '#fff',
    fontSize: 20,
    padding: 20,
    textAlign: 'center',
  },
});
