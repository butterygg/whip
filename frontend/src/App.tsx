import { useState } from "react";
import logo from "./whipped-cream.png";
import "./App.css";

function App() {
  const [address, setAddress] = useState("");

  return (
    <div className="App">
      <header className="App-header">
        <div></div>
        <img src={logo} className="App-logo" alt="logo" />
        <input
          placeholder={address || "Address"}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              setAddress(event.currentTarget.value);
            }
          }}
        ></input>
      </header>
      <div>Address: {address}</div>
    </div>
  );
}

export default App;
