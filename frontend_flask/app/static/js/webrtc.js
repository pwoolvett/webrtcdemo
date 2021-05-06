/* vim: set sts=4 sw=4 et :
 *
 * Demo Javascript app for negotiating and streaming a sendrecv webrtc stream
 * with a GStreamer app. Runs only in passive mode, i.e., responds to offers
 * with answers, exchanges ICE candidates, and streams.
 *
 * Author: Nirbheek Chauhan <nirbheek@centricular.com>
 */



// // // // // // // // // // //  UTILS // // // // // // // // // // // // // // // // // // 

/**
 * @param {String} HTML representing a single element
 * @return {Element}
 */
 function htmlToElement(html) {
    var template = document.createElement('template');
    html = html.trim(); // Never return a text node of whitespace as the result
    template.innerHTML = html;
    return template.content.firstChild;
}

// // // // // // // // // // //  REFERENCE CODE // // // // // // // // // // // // // // // // // // 

// Set this to override the automatic detection in websocketServerConnect()
var ws_server;
var ws_port=7003;
// Set this to use a specific peer id instead of a random one
var default_peer_id = 1;
// Override with your own STUN servers if you want
var rtc_configuration = {iceServers: [{urls: "stun:stun.services.mozilla.com"},
                                      {urls: "stun:stun.l.google.com:19302"}]};
// The default constraints that will be attempted. Can be overriden by the user.
var default_constraints = {};//{video: true, audio: true};

var connect_attempts = 0;
var peer_connection;
var send_channel;
var ws_conn;
// Promise for local stream after constraints are approved by the user
var local_stream_promise;

function getOurId() {
    return Math.floor(Math.random() * (9000 - 10) + 10).toString();
}

function resetState() {
    // This will call onServerClose()
    ws_conn.close();
}

function handleIncomingError(error) {
    setError("ERROR: " + error);
    resetState();
}

function getVideoElement() {
    return document.getElementById("stream");
}

function setStatus(text) {
    console.log(text);
    // var span = document.getElementById("status")
    // // Don't set the status if it already contains an error
    // if (!span.classList.contains('error'))
    //     span.textContent = text;
}

function setError(text) {
    console.error(text);
    // var span = document.getElementById("status")
    // span.textContent = text;
    // span.classList.add('error');
}

function resetVideo() {
    // Release the webcam and mic
    if (local_stream_promise)
        local_stream_promise.then(stream => {
            if (stream) {
                stream.getTracks().forEach(function (track) { track.stop(); });
            }
        });

    // Reset the video element and stop showing the last received frame
    var videoElement = getVideoElement();
    videoElement.pause();
    videoElement.src = "";
    videoElement.load();
}

// SDP offer received from peer, set remote description and create an answer
function onIncomingSDP(sdp) {
    peer_connection.setRemoteDescription(sdp).then(() => {
        setStatus("Remote SDP set");
        if (sdp.type != "offer")
            return;
        setStatus("Got SDP offer");
        local_stream_promise.then((stream) => {
            setStatus("Got local stream, creating answer");
            peer_connection.createAnswer()
            .then(onLocalDescription).catch(setError);
        }).catch(setError);
    }).catch(setError);
}

// Local description was set, send it to peer
function onLocalDescription(desc) {
    console.log("Got local description: " + JSON.stringify(desc));
    peer_connection.setLocalDescription(desc).then(function() {
        setStatus("Sending SDP " + desc.type);
        sdp = {'sdp': peer_connection.localDescription}
        ws_conn.send(JSON.stringify(sdp));
    });
}

function generateOffer() {
    peer_connection.createOffer().then(onLocalDescription).catch(setError);
}

// ICE candidate received from peer, add it to the peer connection
function onIncomingICE(ice) {
    var candidate = new RTCIceCandidate(ice);
    peer_connection.addIceCandidate(candidate).catch(setError);
}

function onServerMessage(event, peer_id) {
    console.log("Received " + event.data);
    switch (event.data) {
        case "HELLO":
            setStatus("Registered with server, waiting for call");
            requestCall(peer_id);
            return;
        default:
            if (event.data.startsWith("ERROR")) {
                handleIncomingError(event.data);
                return;
            }
	    if (event.data.startsWith("OFFER_REQUEST")) {
	      // The peer wants us to set up and then send an offer
              if (!peer_connection)
                  createCall(null).then (generateOffer);
	    }
            else {
                // Handle incoming JSON SDP and ICE messages
                try {
                    msg = JSON.parse(event.data);
                } catch (e) {
                    if (e instanceof SyntaxError) {
                        handleIncomingError("Error parsing incoming JSON: " + event.data);
                    } else {
                        handleIncomingError("Unknown error parsing response: " + event.data);
                    }
                    return;
                }

                // Incoming JSON signals the beginning of a call
                if (!peer_connection)
                    createCall(msg);

                if (msg.sdp != null) {
                    onIncomingSDP(msg.sdp);
                } else if (msg.ice != null) {
                    onIncomingICE(msg.ice);
                } else {
                    handleIncomingError("Unknown incoming JSON: " + msg);
                }
	    }
    }
}

function onServerClose(event) {
    setStatus('Disconnected from server');
    resetVideo();

    if (peer_connection) {
        peer_connection.close();
        peer_connection = null;
    }

    // Reset after a second
    window.setTimeout(websocketServerConnect, 1000);
}

function onServerError(event) {
    setError("Unable to connect to server, did you add an exception for the certificate?")
    // Retry after 3 seconds
    window.setTimeout(websocketServerConnect, 3000);
}

function getLocalStream() {
    // var constraints;
    // var textarea = document.getElementById('constraints');
    // try {
    //     constraints = JSON.parse(textarea.value);
    // } catch (e) {
    //     console.error(e);
    //     setError('ERROR parsing constraints: ' + e.message + ', using default constraints');
    //     constraints = default_constraints;
    // }
    // constraints = default_constraints;
    // console.log(JSON.stringify(constraints));

    // Add local stream
    if (navigator.mediaDevices.getUserMedia) {
        return navigator.mediaDevices.getUserMedia(default_constraints);
    } else {
        errorUserMediaHandler();
    }
}



function websocketServerConnect() {
    connect_attempts++;
    if (connect_attempts > 3) {
        setError("Too many connection attempts, aborting. Refresh page to try again");
        return;
    }
    // Clear errors in the status span
    // var span = document.getElementById("status");
    // span.classList.remove('error');
    // span.textContent = '';
    // Populate constraints
    // var textarea = document.getElementById('constraints');
    // if (textarea.value == '')
    //     textarea.value = JSON.stringify(default_constraints);
    // Fetch the peer id to use
    peer_id = default_peer_id || getOurId();
    ws_port = ws_port || '8443';
    if (window.location.protocol.startsWith ("file")) {
        ws_server = ws_server || "127.0.0.1";
    } else if (window.location.protocol.startsWith ("http")) {
        ws_server = ws_server || window.location.hostname;
    } else {
        throw new Error ("Don't know how to connect to the signalling server with uri" + window.location);
    }
    var ws_url = 'ws://' + ws_server + ':' + ws_port
    setStatus("Connecting to server " + ws_url);
    ws_conn = new WebSocket(ws_url);
    /* When connected, immediately register with the server */
    ws_conn.addEventListener('open', (event) => {
        // document.getElementById("peer-id").textContent = peer_id;
        console.log(`Our peer id: ${peer_id}`)
        ws_conn.send('HELLO ' + peer_id);
        setStatus("Registering with server");
    });
    ws_conn.addEventListener('error', onServerError);
    ws_conn.addEventListener('message', event => onServerMessage(event, peer_id));
    ws_conn.addEventListener('close', onServerClose);
}


function onRemoteTrack(event) {
    var videoElement = getVideoElement();

    if (videoElement.style.display === "none") {
        videoElement.style.display = "block";
        document.getElementById("videoProgressbar").style.display = "none";
      }

    if (videoElement.srcObject !== event.streams[0]) {
        console.log('Incoming stream');
        videoElement.srcObject = event.streams[0];
    }
}

function errorUserMediaHandler() {
    setError("Browser doesn't support getUserMedia!");
}

const handleDataChannelOpen = (event) =>{
    console.log("dataChannel.OnOpen", event);
};

const handleDataChannelMessageReceived = (event) =>{
    console.log("dataChannel.OnMessage:", event, event.data.type);

    setStatus("Received data channel message");
    if (typeof event.data === 'string' || event.data instanceof String) {
        console.log('Incoming string message: ' + event.data);
        textarea = document.getElementById("text");
        textarea.value = textarea.value + '\n' + event.data
    } else {
        console.log('Incoming data message');
    }
    send_channel.send("Hi! (from browser)");
};

const handleDataChannelError = (error) =>{
    console.log("dataChannel.OnError:", error);
};

const handleDataChannelClose = (event) =>{
    console.log("dataChannel.OnClose", event);
};

function onDataChannel(event) {
    setStatus("Data channel created");
    let receiveChannel = event.channel;
    receiveChannel.onopen = handleDataChannelOpen;
    receiveChannel.onmessage = handleDataChannelMessageReceived;
    receiveChannel.onerror = handleDataChannelError;
    receiveChannel.onclose = handleDataChannelClose;
}

function createCall(msg) {
    // Reset connection attempts because we connected successfully
    connect_attempts = 0;

    console.log('Creating RTCPeerConnection');

    peer_connection = new RTCPeerConnection(rtc_configuration);
    send_channel = peer_connection.createDataChannel('label', null);
    send_channel.onopen = handleDataChannelOpen;
    send_channel.onmessage = handleDataChannelMessageReceived;
    send_channel.onerror = handleDataChannelError;
    send_channel.onclose = handleDataChannelClose;
    peer_connection.ondatachannel = onDataChannel;
    peer_connection.ontrack = onRemoteTrack;
    /* Send our video/audio to the other peer */
    local_stream_promise = getLocalStream().then((stream) => {
        console.log('Adding local stream');
        peer_connection.addStream(stream);
        return stream;
    }).catch(setError);

    if (msg != null && !msg.sdp) {
        console.log("WARNING: First message wasn't an SDP message!?");
    }

    peer_connection.onicecandidate = (event) => {
	// We have a candidate, send it to the remote party with the
	// same uuid
	if (event.candidate == null) {
            console.log("ICE Candidate was null, done");
            return;
	}
	ws_conn.send(JSON.stringify({'ice': event.candidate}));
    };

    if (msg != null)
        setStatus("Created peer connection for call, waiting for SDP");

    return local_stream_promise;
}

// // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // 

function listCameras(onsuccess, onFailure) {
    var xhttp = new XMLHttpRequest();
    xhttp.onreadystatechange = function() {
        if (this.readyState == 4) {
            if (this.status == 200) {
                onsuccess(this);
            } else {
                onFailure(this);
            }
        }
    };
    xhttp.open("GET", "/api/list_cameras", true);
    xhttp.send();
}


function changeCamera(camera_id, onSuccess, onFailure) {
    var xhttp = new XMLHttpRequest();
    xhttp.onreadystatechange = function() {
        console.log("RECEIVED changeCamera RESPONSE");
        response=this;
        console.log(this);
        if (this.readyState == 4) {
            if (this.status == 200) {
                onSuccess(this);
            } else {
                onFailure(this);
            }
        }
    };
    xhttp.open("GET", `/api/focus_camera/${camera_id}`, true);
    xhttp.send();
}


function hideVideoProgressbar() {
    document.getElementById("videoProgressbar").style.display = "none";
}

function showVideoProgressbar() {
    document.getElementById("videoProgressbar").style.display = "";
}


function showVideo() {
    getVideoElement().style.display=""
} 

function requestCall(peer_id) {
    setStatus("requesting call");
    var xhttp = new XMLHttpRequest();
    xhttp.onreadystatechange = function() {
        if (this.readyState == 4) {
            if (this.status == 200) {
                console.log("REQUEST call SUCCEEDED");
            } else if (this.status == 101) {
                console.log("websocket connected");
                console.log("requestCall SUCCEEDED");
            } else {
                console.log("REQUEST FAILED");
                console.log(this);
            }
        }
    };
    xhttp.open("GET", `/api/start/${peer_id}`, true);
    xhttp.send();
}


function hideVideoProgressbar() {
    document.getElementById("videoProgressbar").style.display = "none";
}

function showVideoProgressbar() {
    document.getElementById("videoProgressbar").style.display = "";
}


function showVideo() {
    getVideoElement().style.display=""
} 


function setCameraSelectionButtons(cameras) {
    //  TODO: attach to videoPlayer

    onRadioButtonClick = function onRadioButtonClick(camera_id){
        changeCamera(
            camera_id,
            function(xhttp){console.log("CHANGE CAMERA SUCESS")},
            function(xhttp){console.log("CHANGE CAMERA FAILED")},
        );
    }

    let cameraButtons = document.getElementById("cameraButtons")
    cameraButtons.innerHTML = "";

    for (const camera_id of cameras) {
        let radioButton = htmlToElement(`
            <label
              class="mdl-radio mdl-js-radio mdl-js-ripple-effect"
              for="option-${camera_id}"
              onclick="onRadioButtonClick(${camera_id})"
            >
                <input type="radio" id="option-${camera_id}" class="mdl-radio__button" name="options" value="${camera_id}">
                <span class="mdl-radio__label">Cámara ${camera_id}</span>
            </label>        
        `);
        radioButton.onclick = button => onRadioButtonClick(camera_id);
        cameraButtons.appendChild(radioButton);
    }

    return ;
}

// // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // // 
function onLoad() {

    function onSuccess(xhttp){
        console.log("STATUS OK");
        let cameras = JSON.parse(xhttp.response)["cameras"];
        hideVideoProgressbar();
        showVideo();
        setCameraSelectionButtons(cameras);
        websocketServerConnect();
    };

    function onError(xhttp){
        console.log("GOT not 200");
        // window.setTimeout(listCameras.bind(null,onSuccess, onError), 5000);
    }

    listCameras(onSuccess, onError);
}