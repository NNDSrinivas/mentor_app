import React, { useEffect, useState } from "react";
import { View, Text, Button, ScrollView } from "react-native";

export default function ApprovalsScreen() {
  const [items, setItems] = useState([]);

  async function refresh() {
    const r = await fetch("http://YOUR_SERVER_IP:8081/api/approvals");
    const j = await r.json();
    setItems(j.items || []);
  }

  async function resolve(id, decision) {
    await fetch("http://YOUR_SERVER_IP:8081/api/approvals/resolve", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({ id, decision })
    });
    refresh();
  }

  useEffect(() => { refresh(); }, []);

  return (
    <View style={{flex:1, padding:16, backgroundColor:"#000"}}>
      <Text style={{color:"#0f0", fontSize:20, marginBottom:8}}>Approvals</Text>
      <ScrollView>
        {items.map(it => (
          <View key={it.id} style={{borderColor:"#0f0", borderWidth:1, borderRadius:8, padding:12, marginBottom:12}}>
            <Text style={{color:"#0f0"}}>{it.action}</Text>
            <Text style={{color:"#9f9"}} selectable>{JSON.stringify(it.payload, null, 2)}</Text>
            <View style={{flexDirection:"row", gap:12, marginTop:8}}>
              <Button title="Approve" onPress={()=>resolve(it.id,"approve")} />
              <Button title="Reject" onPress={()=>resolve(it.id,"reject")} />
            </View>
          </View>
        ))}
      </ScrollView>
    </View>
  );
}
