using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace BloodborneLauncher.Core
{
    /// <summary>
    /// The Hunter's Dream co-op pool (online_pool=huntersdream): its account, linked with Discord
    /// the way bbhost does it (a device code approved on the website). The token is kept encrypted
    /// in the launcher's settings and passed to the game when it starts; the engine's own
    /// Hunter's Dream backend uses it.
    /// </summary>
    public static class HuntersDream
    {
        /// <summary>The account service: the game server's origin (The Hunter's Dream unless another is set).</summary>
        public static string AuthBase(string gameServer)
        {
            var uri = new Uri(Online.GameServer(gameServer));
            return $"{uri.Scheme}://{uri.Host}";
        }

        private static async Task<JsonObject> CallAsync(HttpClient http, string url, JsonObject body, CancellationToken cancel)
        {
            using var content = new StringContent(body.ToJsonString(), Encoding.UTF8, "application/json");
            using var response = await http.PostAsync(url, content, cancel);
            var text = await response.Content.ReadAsStringAsync(cancel);
            JsonObject? reply = null;
            try { reply = JsonNode.Parse(text) as JsonObject; } catch (JsonException) { }
            if (reply is null || reply["ResKind"] is null)
                throw new InvalidOperationException($"{url} has no account service (HTTP {(int)response.StatusCode})");
            if (reply["ResKind"]!.GetValue<int>() != 0)
                throw new InvalidOperationException(reply["Message"]?.GetValue<string>() ?? "refused");
            return reply;
        }

        /// <summary>Discord sign-in: <paramref name="code"/> gets (page, code) to approve there.
        /// Returns the account's name and token, or throws with the server's reason.</summary>
        public static async Task<(string Name, string Token)> SignInAsync(string gameServer, Action<string, string> code,
            CancellationToken cancel)
        {
            var auth = AuthBase(gameServer);
            using var http = new HttpClient { Timeout = TimeSpan.FromSeconds(10) };
            var device = $"BloodBorneButPc on {Environment.MachineName}";
            var start = await CallAsync(http, auth + "/auth/device/start", new JsonObject { ["DeviceName"] = device }, cancel);
            var deviceCode = start["DeviceCode"]?.GetValue<string>() ?? "";
            var userCode = start["UserCode"]?.GetValue<string>() ?? "";
            if (deviceCode.Length == 0 || userCode.Length == 0) throw new InvalidOperationException("no code in the reply");
            var interval = Math.Max(1, start["Interval"]?.GetValue<int>() ?? 5);
            var expires = DateTime.UtcNow.AddSeconds(start["ExpiresIn"]?.GetValue<int>() ?? 600);
            code(start["VerificationUri"]?.GetValue<string>() ?? auth + "/link", userCode);
            while (DateTime.UtcNow < expires)
            {
                await Task.Delay(TimeSpan.FromSeconds(interval), cancel);
                var poll = await CallAsync(http, auth + "/auth/device/poll", new JsonObject { ["DeviceCode"] = deviceCode }, cancel);
                switch (poll["Status"]?.GetValue<string>())
                {
                    case "approved":
                        var name = poll["OnlineId"]?.GetValue<string>() ?? "";
                        var token = poll["Token"]?.GetValue<string>() ?? "";
                        if (name.Length == 0 || token.Length == 0) throw new InvalidOperationException("no token in the reply");
                        return (name, token);
                    case "slow_down":
                        interval += 5;
                        break;
                    case "denied":
                        throw new InvalidOperationException("the sign-in was denied");
                    case "expired":
                        throw new InvalidOperationException("the code expired; try again");
                }
            }
            throw new InvalidOperationException("the code expired; try again");
        }

        /// <summary>Tells the server to forget the token (best effort).</summary>
        public static async Task SignOutAsync(string gameServer, string token)
        {
            try
            {
                using var http = new HttpClient { Timeout = TimeSpan.FromSeconds(5) };
                await CallAsync(http, AuthBase(gameServer) + "/auth/logout", new JsonObject { ["Token"] = token }, CancellationToken.None);
            }
            catch (Exception)
            {
            }
        }
    }
}
