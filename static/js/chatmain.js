RSABits = 2048;
chatsalt = "SAAAAAAAAAAAAAAAAAAAAAAAAAAAALT";

jQuery.fn.serializeObject = function() {
  var arrayData, objectData;
  arrayData = this.serializeArray();
  objectData = {};

  $.each(arrayData, function() {
    var value;

    if (this.value != null) {
      value = this.value;
    } else {
      value = '';
    }

    if (objectData[this.name] != null) {
      if (!objectData[this.name].push) {
        objectData[this.name] = [objectData[this.name]];
      }

      objectData[this.name].push(value);
    } else {
      objectData[this.name] = value;
    }
  });

  return objectData;
};

function getKey(password)
{
	return cryptico.generateRSAKey(password, RSABits);
}

function getPubKey(password)
{
	return cryptico.publicKeyString(getKey(password));
}

function decryptRSA(password,what)
{
	return cryptico.decrypt(what,getKey(password)).plaintext;
}

function encryptRSA(pubkey,what)
{
	return cryptico.encrypt(what,pubkey).cipher;
}

function passtoAES(pass)
{
	Math.seedrandom(sha256.hex("AES1"+pass+"AES2"));
    var r = new SeededRandom();
    var key = new Array(32);
    r.nextBytes(key);
    return key;
}

function encryptAESPWD(key,what)
{
	return cryptico.encryptAESCBC(what,passtoAES(key));
}

function decryptAESPWD(key,what)
{
	return cryptico.decryptAESCBC(what,passtoAES(key));
}

function encryptAES(key,what)
{
	return cryptico.encryptAESCBC(what,key);
}

function decryptAES(key,what)
{
	return cryptico.decryptAESCBC(what,key);
}

function getHash(what)
{
	return MD5(SHA1(chatsalt+what));
}

function gensafekey()
{
	return cryptico.generateAESKey();
}

function keytob64(key)
{
	return btoa(cryptico.bytes2string(key));
}

function b64tokey(b64)
{
	return cryptico.string2bytes(atob(b64));
}
