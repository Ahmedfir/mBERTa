# Pit : Pit 1.9.4
command-line jar build with dependencies form:
* https://github.com/hcoles/pitest.git
* master branch
* revision: 17e1eecf

# Pit-rv : Pit 1.7.4
command-line jar build with dependencies form:
* https://github.com/hcoles/pitest.git
* master branch
* revision: 2ec1178a

to build with dependencies, under <build> <plugins>, add:

	<plugin>
				<groupId>org.apache.maven.plugins</groupId>
				<artifactId>maven-assembly-plugin</artifactId>
				<executions>
					<execution>
						<phase>package</phase>
						<goals>
							<goal>single</goal>
						</goals>
						<configuration>
							<archive>
								<manifest>
									<mainClass>
										org.pitest.mutationtest.commandline.MutationCoverageReport
									</mainClass>
								</manifest>
							</archive>
							<descriptorRefs>
								<descriptorRef>jar-with-dependencies</descriptorRef>
							</descriptorRefs>
						</configuration>
					</execution>
				</executions>
			</plugin>