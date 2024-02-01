# 3 avantages de l'injection de dépendance, illustrés avec le cas de l'allocation mémoire dans le language Zig

## Contexte
En s'intéressant au language [Zig](https://ziglang.org/), j'ai trouvé que ses conventions concernant l'allocation émmoire étaient une bonne illustration de certains avantages du pattern d'injection de dépendances. Cet article ce concentre sur certains de ces avantages, en illustrant chacun d'eux avec un exemple 'bonus' en Zig en plus de languages plus classiques.

Le code source correspondant à l'article est disponible sur Github à l'addresse https://github.com/Brice-sogilis/di-post/tree/main

## Terminologie

### Injection de dépendance

- Dans ce document, on utilise le terme Injection de Dépendance pour un cas d'application spécifique du pattern "Straégie". On désigne par Injection de dépendance le principe de fournir des implémentations spécifiques de comportements ou des ressources à un composant(classe, fonction, module ...) d'un système au lieu de laisser chaque composant instancier ou acquérir ces ressources par lui même. On restreint ainsi le champs des responsabilités de chaque composant à son domaine spécifique, et la gestion des ressources peut être centralisée ou modularisée.
- On n'utilise **pas** le terme d'iInjection de Dépendance pour désigner les framework associés, comme Sring ou Guice, dont le rôle est de faciliter la gestion "mécanique" de l'application de ce pattern dans une base de code, par exemple en automatisant l'injection de paramètre à l'aide d'annotations. 


### Allocation mémoire

Dans certains language la gestion de la mémoire est automatisée, que ce soit par un [garbage collector](https://en.wikipedia.org/wiki/Garbage_collection_(computer_science))(Java, C#, Javascript, OCaml…) ou par du code généré par le compilateur (C++ [destructors](https://www.geeksforgeeks.org/destructors-c/), [Rust](https://www.rust-lang.org/) …).
Dans d'autre, particulièrement le [C](https://en.wikipedia.org/wiki/C_dynamic_memory_allocation), allouer et librérer la mémoire relève de la responsabilité du programmeur. Des objets ou structures de données créés dynamiquement (i.e. de manière non-bornée à la compilation) doivent être explicitement libérées par des fonctions dédiées, ce qui implique de respecter certaines conventions de "propriétés" de ces données afin de s'assurer que de la mémoire allouée ne fuitera pas en n'étant jamais libérée ("memory-leak") ou bien, à l'inverse, que plusieurs zones du code n'essayeront pas de nettoyer plusieurs fois la même zone mémoire ("double-free").

## Avantages de l'injection de dépendances

Nous allons traiter de trois principales 'features' implémentée avec l'injection de dépendances: 

+ Le contrôle de ressources critiques

+ La modularité du code permettant sa testabilité

+ La mise en évidence des dépendances d'un composant

## 1) Contrôle de ressources critiques

Sans injection de dépendances, chaque composant est responsable d'allouer ses propres ressources à la volée. Ces ressources peuvent être des threads, de la mémoire, des fichiers partagés, une connection à une base de données... Avec le temps, le système se complexifiant, le nombre et l'intrication de ces composants va croître, et cette approche où "chacun se sert à volonté" peut mener à des conflits ou a des situation de famine dans d'autres parties du système. Considérons le code Java suivant, qui alloue plusieurs threads pour paralléliser un calcul:


```java source=java/Example.java lines=6-22
class Compute {
    public int run() throws ExecutionException, InterruptedException {
        // Allocate 10 threads
        final var threadPool = new ForkJoinPool(10);
        try {
            return threadPool.submit(() ->
                List.of(1,2,3,4,5,6,7,8,9,10)
                .parallelStream() // Run the subsequent map in parallel
                .map(n -> n * 2) // Multiply by 2 each value
                .reduce(0, (a,b) -> a + b)) // Sum each result=)
                .get();

        } finally {
            threadPool.shutdown();
        }
    }
}
```

Cela fonctionne sans soucis quand on génère seulement une ou quelques instances de `Compute` à la racine de l'application, mais celà peut rapidement devenir une source de surcharge si un grand nombre d'instances sont utilisées, dépassant le nombre de thread que la machine peut effectivement faire tourner en parallèle, et d'autant plus si on considère que chacun des threads requiert un grande quantité de mémoire, qui ne pourra pas être libérée avant la complétion du calcul. De plus, en tant que programmeur de ce code on doit s'assurer de fermer le `threadPool` à la fin du calcul. Dans cette approche, chaque classe qui utilise des threads doit effectuer la même gestion de fermeture, mélangeant ses responsabilités métier avec ces tâches 'd'intendance', propices aux erreurs ou oublis.   

En modifiant le code ainsi :

```java source=java/Example.java lines=24-35
class ComputeWithInjectedResource {
    // threadPool is now passed by the caller of the computation
    public int run(ForkJoinPool threadPool) throws ExecutionException, InterruptedException {
          return threadPool.submit(() ->
                List.of(1,2,3,4,5,6,7,8,9,10)
                  .parallelStream() // Run the subsequent map in parallel
                  .map(n -> n * 2) // Multiply by 2 each value
                  .reduce(0, (a,b) -> a + b)) // Sum each result
                  .get(); // Collect
        
    }
}
```

La responsabilité d'allouer les threads appartient maintenant à l'appelant de la méthode run, qui peut limiter le nombre de threads disponibles, gérer une file de priorité, etc.
De plus, on n'a plus besoin de gérer la logique de fermeture du threadPool, qui peut être centralisée dans un composant dédiée, limitant le risque d'erreur.

### Exemple Zig

En C, l'allocation mémoire peut être effectuée depuis n'importe quelle zone du code, en utilisant la fonction standard `malloc`. Une fonction "gourmande" peut allouer plus de mémoire qu'on ne le souhaiterait, forçant chaque composant à être responsable d'allouer et librérer la mémoire requise à son fonctionnement et de gérer es erreurs potentielles. Par exemple, une implémentation du chiffrage de césar:

```c source=c/example.c lines=5-14
const  char * caesarCiphered(unsigned char offset, const  char * clearText, unsigned  int textLength) {
	char * result = malloc(textLength); // Caller choose the right amount of memory to allocate
	// char * result = malloc(textLength * 3); Nothing would stop us if we tried to allocate more than necessary

	for(unsigned  int i = 0; i< textLength; i++) {
		result[i] = clearText[i] + offset;
	}

	return result;
}
```
En cas d'erreur d'allocation, on se repose sur la fonction pour gérer la situation ou crasher.

En Zig, la convention est d'injecter un 'allocator':

```zig source=zig/example.zig lines=3-13
fn caesarCiphered(allocator: std.mem.Allocator, offset: u8, clearText: []const u8) ![]const u8 {
    const result = try allocator.alloc(u8, clearText.len); // **try** transfer the potential error thrown by allocate(), ence the '!' in the function return type

    // const result = try allocator.allocate(u8, clearText.len * 3); // Here the actual implementation of allocator could limit raise an error if we tried to allocate more bytes than nnecessary

    for (0..clearText.len) |i| {
        result[i] = clearText[i] +% offset; // +% performs modular arithmetic to wrap in 0-255 range
    }

    return result;
}
```

L'appelant contrôle maintenant la logique d'allocation mémoire. Il peut lever une erreur si la fonction essaye d'allouer plus de mémoire que prévu ou disponible. En cas d'erreur, l'appelant est responsable de sa gestion et des potentielles stratégies à appliquer, libérant la fonction de cette responsabilité.

## 2) Testability

Un autre avantage de l'injection de dépendances est de faciliter les tests unitaires d'un composant. Considérons la fonction NodeJS suivante, où l'on souhaite transmettre un message vers différents destinataires en fonction de son contenu:


```ts source=node/example.ts lines=1-9
import axios from "axios";

async function relayMessageToRelevantPeople(message: string) {
  if (message.match("CONFIDENTIAL")) {
    await axios.post("http://vip/mailbox", { message: message });
  } else {
    await axios.post("http://everyone/mailbox", { message: message });
  }
}
```

Le choix du protocole (http) et la connaissance des urls sont inclus dans la fonction. Celà amène des complications pour la tester: pour tester ce dont on ce préoccupe, la logique de discrimination du message, le setup de test devient ardu:


```ts source=node/example.ts lines=29-46
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
```

*[la documentation de nock](https://www.npmjs.com/package/nock#axios)*

Il faut mettre en place un mécanisme d'interception http, et même ce test relativement simple est bruité par les éléments liées au réseau qui l'entourent.

Si l'on change de protocole ou de canal de communication (event bus, mail ...) il faudra mettre à jour ces tests (qui testent pourtant une autre responsabilité) et trouver un autre framework de mock/interception.

On peut abstraire et injecter les canaux de communications 'vip' et 'everyone':

```ts source=node/example.ts lines=11-25
interface Channel {
  // type of an async function accepting a string and returning void
  (message: string): Promise<void>;
}

async function relayMessageToRelevantChannel(
  message: string,
  channels: { sendVip: Channel; sendEveryone: Channel },
) {
  if (message.match("CONFIDENTIAL")) {
    await channels.sendVip(message);
  } else {
    await channels.sendEveryone(message);
  }
}
```

Le test ne requiert plus de setup spécifique à http:

```ts source=node/example.ts lines=48-76
describe("relayMessageToRelevantPeople with channel injection", function () {
  it("redirect confidential messages only to vip(s)", async function () {
    // Setup our mocks without needing http
    let vipCalled = false; // A flag indicating that the vip channel mock has been called
    const vipChannel = async (_: string) => {
      vipCalled = true;
    }; // A mock only updating our flag when called
    const everyoneChannel = async (_: string) => {}; // A mock doing nothing

    await relayMessageToRelevantChannel("this is CONFIDENTIAL", {
      sendVip: vipChannel,
      sendEveryone: everyoneChannel,
    });
    assert.equal(vipCalled, true);
  });

  it("redirect other messages to everyone", async function () {
    let everyoneCalled = false;
    const everyoneChannel = async (msg: string) => {
      everyoneCalled = true;
    };
    const vipChannel = async (msg: string) => {};
    await relayMessageToRelevantChannel("this is CONFITURE", {
      sendVip: vipChannel,
      sendEveryone: everyoneChannel,
    });
    assert.equal(everyoneCalled, true);
  });
});
```

### Exemple Zig

La détection et la prévention de fuites mémoires a motivé le dévelopment de beaucoup d'outil d'analyse, comme [AddressSanitizer](https://clang.llvm.org/docs/AddressSanitizer.html) ou [Valgrind](https://valgrind.org/). Ces outils externes demandent un effort supplémentaire pour les intégrer dans un process de CI par exemple, particulièrement si l'on souhaite vérifier plusieurs composants de manière isolée. Ils requièrenet un apprentissage voire de l'expertise, en plus du language de développement. Bien que n'étant pas aussi exhaustif, l'allocator de la librairie standard Zig `std.testing.allocator` tire parti de l'injection de dépendances pour détecter un large pan de bugs liés à l'allocation mémoire, et est beaucoup moins coûteux à mettre en place au niveau unitaire, détectant les memory leak et les double-free:

```zig source=zig/example.zig lines=26-46
test "This would pass" {
    var list = std.ArrayList(i32).init(std.testing.allocator); // here we inject the testing allocator, which will track all memory allocations performed by list
    defer list.deinit(); // ensure list memory will be freed at the end of the scope
    try list.append(42);
    try std.testing.expect(list.items[0] == 42);
}

test "Detecting a memory leak" {
    var list = std.ArrayList(i32).init(std.testing.allocator);
    try list.append(42);
    try std.testing.expect(list.items[0] == 42);

    // list was not freed !
    std.debug.print("Expected memory leaks logs here, keeep calm ===> \n", .{});
    const detectLeak = std.testing.allocator_instance.detectLeaks();
    std.debug.print("\n<=== End of expected memory leaks logs", .{});
    try std.testing.expect(detectLeak == true);

    // if we do not actually free the list, the test would fail, helping us detecting memory leaks at test time without additionnal tools
    list.deinit();
}
```

## 3) Mise en évidence des dépendances d'un composant
Le dernier point est plus simple mais peut être sous-estimé: si chaque ressource ou comportement externe est injecté au lieu d'être instancié au sein des composants, les signatures des fonctions/méthodes/classes révèlent explicitement leur dépendances et besoins, et possiblement des étrangetés dans le design. Par exemple, avoir besoin de paramètres I/O, comme un accès au système de fichier ou une requête à la base de donnée, au sein de fonction censées être purement logiques: 

```kotlin
// Writing debug files in the middle of a geometric operation ?

// Implicitely
fun splitPolygonInSegments(polygon: Polygon): List<Segment> {
	// ...    
	plotSegment(s, "/debug/segment_image.png")
	// ...
}

// Explicitely
fun splitPolygonInSegments(polygon: Polygon, debugDir: Path?): List<Segment> {
	// ...    
	plotSegment(s, debugDir / "segment_image.png")
	// ...
}

// And maybe the debug output part should be done elsewhere
fun onlySplitPolygonInSegments(polygon: Polygon): List<Segment> {
	// ...    
	// ...
}
```

### Exemple Zig

Il n'est pas toujours nécessaire d'allouer de la mémoire. En étant forcer à passer explicitement un allocator quand on a besoin de mémoire dynamique, on est plus poussé à réfléchir à une solution plus simple ou efficiente, par exemple en se passant de structures de données intermédiaires:


```zig source=zig/example.zig lines=48-72
fn sumOddNumbers(numbers: []const u32) u32 {
    var res: u32 = 0;
    for (numbers) |n| {
        if (n % 2 == 1) res += n;
    }
    return res;
}

fn sumOddNumbersInTwoPhases(allocator: std.mem.Allocator, numbers: []const u32) !u32 {
    var oddNumbers = std.ArrayList(u32).init(allocator);
    defer oddNumbers.deinit();

    // First select odd numbers
    for (numbers) |n| {
        if (n % 2 == 1) try oddNumbers.append(n);
    }

    // Then sum them
    var res: u32 = 0;
    for (oddNumbers.items) |n| {
        res += n;
    }

    return res;
}
```

Note: il ya cependant un compromis à trouver entre efficacité et lisibilité, adapter les algorithmes pour éviter d'allouer de la mémoire dyanamique pouvant aussi les rendre plus complexe