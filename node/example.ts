import axios from "axios";

async function relayMessageToRelevantPeople(message: string) {
  if (message.match("CONFIDENTIAL")) {
    await axios.post("http://vip/mailbox", { message: message });
  } else {
    await axios.post("http://everyone/mailbox", { message: message });
  }
}

interface Channel {
  // type of an async function accepting a string and returning void
  (message: string): Promise<void>;
}

async function relayMessageToRelevantChannel(
  message: string,
  channels: [Channel, Channel],
) {
  const [sendVip, sendEveryone] = channels; // destructure channels
  if (message.match("CONFIDENTIAL")) {
    await sendVip(message);
  } else {
    await sendEveryone(message);
  }
}

// Tests
import assert from "assert";
import nock from "nock"; // Http & DNS mocking framework
axios.defaults.adapter = "http"; // Allows nock to intercept axios requests

describe("relayMessageToRelevantPeople", function () {
  it("redirect confidential messages only to vip(s)", async function () {
    const scope = nock("http://vip") // intercepts request to this hostname
      .post("/mailbox") // expect a post request to /mailbox
      .reply(200, "OK"); // reply with OK when requested
    await relayMessageToRelevantPeople("this is CONFIDENTIAL");
    scope.done(); // Will fail if the expected request was not received
  });

  it("redirect other messages to everyone", async function () {
    const scope = nock("http://everyone").post("/mailbox").reply(200, "OK");
    await relayMessageToRelevantPeople("this is CONFITURE");
    scope.done();
  });
});

describe("relayMessageToRelevantPeople with channel injection", function () {
  it("redirect confidential messages only to vip(s)", async function () {
    // Setup our mocks without needing http
    let vipCalled = false; // A flag indicating that the vip channel mock has been called
    const vipChannel = async (_: string) => {
      vipCalled = true;
    }; // A mock only updating our flag when called
    const everyoneChannel = async (_: string) => {}; // A mock doiing nothing

    await relayMessageToRelevantChannel("this is CONFIDENTIAL", [
      vipChannel,
      everyoneChannel,
    ]);
    assert.equal(vipCalled, true);
  });

  it("redirect other messages to everyone", async function () {
    let everyoneCalled = false;
    const everyoneChannel = async (msg: string) => {
      everyoneCalled = true;
    };
    const vipChannel = async (msg: string) => {};
    await relayMessageToRelevantChannel("this is CONFITURE", [
      vipChannel,
      everyoneChannel,
    ]);
    assert.equal(everyoneCalled, true);
  });
});
